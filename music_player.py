"""
music_player.py — Jarvis AI Alexa Skill
YouTube API v3 for search + Piped proxy stream URLs for playback.
Piped /streams endpoint returns its own proxy URLs (no cookies needed).
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YoutubeAPIKey", "")
HEADERS = {"User-Agent": "Mozilla/5.0"}

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.projectsegfau.lt",
    "https://pipedapi.bocchi.rocks",
    "https://piped-api.garudalinux.org",
]


def _youtube_search(query: str):
    """Search via YouTube Data API v3. Returns (video_id, title)."""
    if not YOUTUBE_API_KEY:
        logger.error("YoutubeAPIKey not set!")
        return None, None
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoCategoryId": "10",
                "maxResults": 1,
                "key": YOUTUBE_API_KEY,
            },
            timeout=8,
        )
        if r.status_code != 200:
            logger.error(f"YouTube API {r.status_code}: {r.text[:200]}")
            return None, None
        items = r.json().get("items", [])
        if not items:
            return None, None
        video_id = items[0]["id"]["videoId"]
        title = items[0]["snippet"]["title"]
        logger.info(f"Found: '{title}' id={video_id}")
        return video_id, title
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return None, None


def _get_piped_stream(video_id: str):
    """
    Get audio stream URL from Piped.
    Piped returns its own proxy URLs (e.g. /videoplayback?...) which
    don't require YouTube cookies and are directly streamable by Alexa.
    We prefer audio/mp4 (AAC) over audio/webm (opus) for Alexa compatibility.
    """
    for instance in PIPED_INSTANCES:
        try:
            r = requests.get(
                f"{instance}/streams/{video_id}",
                headers=HEADERS,
                timeout=8,
            )
            if r.status_code != 200:
                logger.warning(f"Piped {instance} returned {r.status_code}")
                continue

            data = r.json()
            audio_streams = data.get("audioStreams", [])
            if not audio_streams:
                logger.warning(f"No audio streams from {instance}")
                continue

            logger.info(f"Got {len(audio_streams)} streams from {instance}")
            for s in audio_streams:
                logger.info(f"  mime={s.get('mimeType')} bitrate={s.get('bitrate')} url={s.get('url','')[:60]}")

            # Sort by bitrate descending
            audio_streams.sort(key=lambda x: x.get("bitrate", 0), reverse=True)

            # First pass: prefer audio/mp4 (AAC) — Alexa compatible
            for s in audio_streams:
                mime = s.get("mimeType", "")
                url = s.get("url", "")
                if "mp4" in mime and url:
                    logger.info(f"Selected mp4 stream: {mime} @ {s.get('bitrate')}bps")
                    return url

            # Second pass: any audio format
            for s in audio_streams:
                url = s.get("url", "")
                if url:
                    mime = s.get("mimeType", "")
                    logger.info(f"Fallback stream: {mime} @ {s.get('bitrate')}bps")
                    return url

        except Exception as e:
            logger.warning(f"Piped {instance} error: {e}")
            continue

    return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    url = _get_piped_stream(video_id)
    if url:
        return url, title, None

    logger.error(f"All Piped instances failed for {video_id}")
    return None, None, None

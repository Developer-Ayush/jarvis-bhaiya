"""
music_player.py — Jarvis AI Alexa Skill
YouTube API v3 for search + Invidious for stream URLs.
Piped is dead — using Invidious instances instead.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YoutubeAPIKey", "")
HEADERS = {"User-Agent": "Mozilla/5.0"}

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.privacyredirect.com",
    "https://yt.cdaut.de",
    "https://invidious.nerdvpn.de",
    "https://iv.melmac.space",
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
        title    = items[0]["snippet"]["title"]
        logger.info(f"Found: '{title}' id={video_id}")
        return video_id, title
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return None, None


def _get_invidious_stream(video_id: str):
    """
    Get audio stream URL from Invidious.
    Tries multiple instances with fallback.
    Prefers audio/mp4 (AAC) for Alexa compatibility.
    """
    for instance in INVIDIOUS_INSTANCES:
        try:
            r = requests.get(
                f"{instance}/api/v1/videos/{video_id}",
                headers=HEADERS,
                params={"fields": "adaptiveFormats,title"},
                timeout=8,
            )
            if r.status_code != 200:
                logger.warning(f"Invidious {instance} returned {r.status_code}")
                continue

            data = r.json()
            formats = data.get("adaptiveFormats", [])
            if not formats:
                logger.warning(f"No adaptive formats from {instance}")
                continue

            # Filter audio-only formats
            audio_formats = [
                f for f in formats
                if f.get("type", "").startswith("audio")
                and f.get("url")
            ]

            if not audio_formats:
                logger.warning(f"No audio formats from {instance}")
                continue

            logger.info(f"Got {len(audio_formats)} audio formats from {instance}")

            # Sort by bitrate descending
            audio_formats.sort(
                key=lambda x: int(x.get("bitrate", 0)), reverse=True
            )

            # First pass: prefer audio/mp4 (AAC) — best Alexa compatibility
            for f in audio_formats:
                mime = f.get("type", "")
                url  = f.get("url", "")
                if "mp4" in mime and url:
                    logger.info(f"Selected mp4 stream: {mime}")
                    return url

            # Fallback: any audio format
            url = audio_formats[0].get("url")
            if url:
                logger.info(f"Fallback stream: {audio_formats[0].get('type')}")
                return url

        except Exception as e:
            logger.warning(f"Invidious {instance} error: {e}")
            continue

    logger.error("All Invidious instances failed")
    return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    url = _get_invidious_stream(video_id)
    if url:
        return url, title, None

    logger.error(f"All instances failed for {video_id}")
    return None, None, None

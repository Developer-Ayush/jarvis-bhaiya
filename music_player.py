"""
music_player.py — Jarvis AI Alexa Skill
Uses YouTube Data API v3 for reliable search (1 unit/request).
Uses Piped/Invidious instances for stream URL extraction (no API key needed).
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
    "https://pa.il.ax",
]

INVIDIOUS_INSTANCES = [
    "https://invidious.snopyta.org",
    "https://yewtu.be",
    "https://invidious.kavin.rocks",
    "https://inv.riverside.rocks",
    "https://invidious.projectsegfau.lt",
]


def _youtube_search(query: str):
    if not YOUTUBE_API_KEY:
        logger.error("YoutubeAPIKey env var not set!")
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
            logger.error(f"YouTube API error {r.status_code}: {r.text}")
            return None, None
        data = r.json()
        items = data.get("items", [])
        if not items:
            return None, None
        video_id = items[0]["id"]["videoId"]
        title = items[0]["snippet"]["title"]
        logger.info(f"YouTube API found: '{title}' (id={video_id})")
        return video_id, title
    except Exception as e:
        logger.error(f"YouTube API search error: {e}", exc_info=True)
        return None, None


def _stream_from_piped(video_id: str):
    for instance in PIPED_INSTANCES:
        try:
            r = requests.get(f"{instance}/streams/{video_id}", headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            audio_streams = r.json().get("audioStreams", [])
            if not audio_streams:
                continue
            audio_streams.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
            for stream in audio_streams:
                mime = stream.get("mimeType", "")
                url = stream.get("url", "")
                if ("mp4" in mime or "aac" in mime or "mp3" in mime) and url:
                    logger.info(f"Piped stream via {instance}: {mime}")
                    return url
            url = audio_streams[0].get("url")
            if url:
                return url
        except Exception as e:
            logger.warning(f"Piped {instance} failed: {e}")
    return None


def _stream_from_invidious(video_id: str):
    for instance in INVIDIOUS_INSTANCES:
        try:
            r = requests.get(
                f"{instance}/api/v1/videos/{video_id}",
                params={"fields": "adaptiveFormats,title"},
                headers=HEADERS,
                timeout=8,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            formats = data.get("adaptiveFormats", [])
            audio = [f for f in formats if f.get("type", "").startswith("audio")]
            if not audio:
                continue
            audio.sort(key=lambda x: int(x.get("bitrate", 0)), reverse=True)
            for fmt in audio:
                mime = fmt.get("type", "")
                url = fmt.get("url", "")
                if ("mp4" in mime or "aac" in mime or "mp3" in mime) and url:
                    logger.info(f"Invidious stream via {instance}: {mime}")
                    return url
            url = audio[0].get("url")
            if url:
                return url
        except Exception as e:
            logger.warning(f"Invidious {instance} failed: {e}")
    return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None) on failure.
    Flow: YouTube API v3 search → Piped stream → Invidious stream fallback
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    stream_url = _stream_from_piped(video_id)
    if stream_url:
        return stream_url, title, None

    logger.warning(f"Piped failed, trying Invidious for {video_id}")
    stream_url = _stream_from_invidious(video_id)
    if stream_url:
        return stream_url, title, None

    logger.error(f"All stream sources failed for: {title} ({video_id})")
    return None, None, None

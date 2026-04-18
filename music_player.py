"""
music_player.py — Jarvis AI Alexa Skill
YouTube Data API v3 for search + Cobalt API for stream extraction.
Cobalt is free, no key needed, works from Vercel.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YoutubeAPIKey", "")
HEADERS = {"User-Agent": "Mozilla/5.0"}

COBALT_INSTANCES = [
    "https://api.cobalt.tools",
    "https://cobalt.ayaka.io",
    "https://cobalt-api.kwiatekmiki.com",
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


def _cobalt_stream(video_id: str):
    """
    Get audio stream URL from Cobalt API.
    Tries multiple instances with fallback.
    """
    yt_url = f"https://www.youtube.com/watch?v={video_id}"

    for instance in COBALT_INSTANCES:
        try:
            r = requests.post(
                instance,
                json={
                    "url": yt_url,
                    "downloadMode": "audio",
                    "audioFormat": "best",
                    "filenameStyle": "basic",
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
                timeout=10,
            )

            if r.status_code != 200:
                logger.warning(f"Cobalt {instance} returned {r.status_code}: {r.text[:100]}")
                continue

            data = r.json()
            status = data.get("status")
            url    = data.get("url")

            logger.info(f"Cobalt {instance} status={status} url={str(url)[:60]}")

            # stream / redirect / tunnel — all are directly usable by Alexa
            if status in ("stream", "redirect", "tunnel") and url:
                return url

            # picker returns a list — grab the first audio item
            if status == "picker":
                for item in data.get("picker", []):
                    if item.get("url"):
                        return item["url"]

        except Exception as e:
            logger.warning(f"Cobalt {instance} error: {e}")
            continue

    logger.error("All Cobalt instances failed")
    return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    Flow: YouTube Data API v3 search → Cobalt stream extraction
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    url = _cobalt_stream(video_id)
    if url:
        return url, title, None

    logger.error(f"Cobalt failed for: {title} ({video_id})")
    return None, None, None

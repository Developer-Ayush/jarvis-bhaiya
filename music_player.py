"""
music_player.py — Jarvis AI Alexa Skill
YouTube API v3 for search + Invidious proxy for AAC stream (itag=140).
itag 140 = audio/mp4 AAC 128kbps — fully supported by Alexa AudioPlayer.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YoutubeAPIKey", "")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Only use instances confirmed working (200) from logs
INVIDIOUS_INSTANCES = [
    "https://invidious.projectsegfau.lt",
    "https://api.piped.projectsegfau.lt",
    "https://yewtu.be",
    "https://invidious.nerdvpn.de",
    "https://iv.datura.network",
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
                "videoCategoryId": "10",  # Music
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


def _invidious_proxy_url(instance: str, video_id: str) -> str:
    """
    Build an Invidious proxy URL for itag 140 (audio/mp4 AAC 128kbps).
    Alexa can stream this directly. No parsing needed.
    """
    return f"{instance}/latest_version?id={video_id}&itag=140&local=true"


def _check_url(url: str) -> bool:
    """Check if URL is reachable and returns audio content."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=6, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        ok = r.status_code == 200 and ("audio" in ct or "video" in ct or "octet" in ct)
        logger.info(f"URL check {r.status_code} ct={ct} ok={ok}: {url[:80]}")
        return ok
    except Exception as e:
        logger.warning(f"URL check failed: {e}")
        return False


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    Flow: YouTube API v3 → Invidious proxy (itag=140 AAC)
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    # Try each Invidious instance proxy URL
    for instance in INVIDIOUS_INSTANCES:
        url = _invidious_proxy_url(instance, video_id)
        if _check_url(url):
            logger.info(f"Using proxy: {instance}")
            return url, title, None
        logger.warning(f"Instance failed: {instance}")

    logger.error(f"All Invidious instances failed for {video_id}")
    return None, None, None

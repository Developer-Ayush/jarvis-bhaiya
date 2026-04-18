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


def _resolve_stream_url(instance: str, video_id: str):
    """
    Follow the Invidious /latest_version redirect to get the real CDN URL.
    Without local=true, Invidious redirects to the actual YouTube CDN URL.
    These are direct mp4/aac files Alexa can stream.
    """
    proxy_url = f"{instance}/latest_version?id={video_id}&itag=140"
    try:
        r = requests.get(
            proxy_url,
            headers=HEADERS,
            timeout=8,
            allow_redirects=True,
            stream=True,  # Don't download body, just follow redirects
        )
        # The final URL after all redirects is the real CDN URL
        final_url = r.url
        ct = r.headers.get("Content-Type", "")
        logger.info(f"Resolved: status={r.status_code} ct={ct} url={final_url[:80]}")
        if r.status_code == 200 and final_url != proxy_url:
            return final_url
        # If no redirect happened but status is 200, try returning the proxy url
        if r.status_code == 200:
            return proxy_url
        return None
    except Exception as e:
        logger.warning(f"Resolve failed for {instance}: {e}")
        return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    Flow: YouTube API v3 → Invidious redirect → real CDN URL
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    for instance in INVIDIOUS_INSTANCES:
        url = _resolve_stream_url(instance, video_id)
        if url:
            logger.info(f"Stream URL resolved via {instance}: {url[:80]}")
            return url, title, None
        logger.warning(f"Instance failed: {instance}")

    logger.error(f"All Invidious instances failed for {video_id}")
    return None, None, None

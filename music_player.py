"""
music_player.py — Jarvis AI Alexa Skill
YouTube Data API v3 for search + RapidAPI YouTube MP3 for stream URL.
"""

import os
import requests
import logging
import time

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YoutubeAPIKey", "")
RAPIDAPI_KEY    = os.environ.get("RapidAPIKey", "")
HEADERS         = {"User-Agent": "Mozilla/5.0"}


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


def _rapidapi_stream(video_id: str):
    """
    Get MP3 stream URL via RapidAPI YouTube MP36.
    Polls until ready (usually 2-5 seconds).
    """
    if not RAPIDAPI_KEY:
        logger.error("RapidAPIKey not set!")
        return None

    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com",
    }

    try:
        # Step 1 — Request conversion
        r = requests.get(
            "https://youtube-mp36.p.rapidapi.com/dl",
            params={"id": video_id},
            headers=headers,
            timeout=15,
        )

        if r.status_code != 200:
            logger.error(f"RapidAPI status {r.status_code}: {r.text[:200]}")
            return None

        data = r.json()
        logger.info(f"RapidAPI response: {data}")

        status = data.get("status")

        # Already done
        if status == "ok":
            url = data.get("link")
            if url:
                logger.info(f"RapidAPI got URL immediately: {url[:60]}")
                return url

        # Processing — poll up to 10 seconds
        if status == "processing":
            for attempt in range(5):
                time.sleep(2)
                r2 = requests.get(
                    "https://youtube-mp36.p.rapidapi.com/dl",
                    params={"id": video_id},
                    headers=headers,
                    timeout=15,
                )
                if r2.status_code == 200:
                    d2 = r2.json()
                    logger.info(f"Poll {attempt+1}: {d2}")
                    if d2.get("status") == "ok":
                        url = d2.get("link")
                        if url:
                            return url
                else:
                    logger.warning(f"Poll {attempt+1} failed: {r2.status_code}")

        logger.error(f"RapidAPI failed: {data}")
        return None

    except Exception as e:
        logger.error(f"RapidAPI error: {e}")
        return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    Flow: YouTube Data API v3 search → RapidAPI MP3 extraction
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    url = _rapidapi_stream(video_id)
    if url:
        return url, title, None

    logger.error(f"RapidAPI failed for: {title} ({video_id})")
    return None, None, None

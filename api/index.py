"""
music_player.py — Jarvis AI Alexa Skill
YouTube Data API v3 for search + yt-dlp for stream URL extraction.
Uses pre-muxed audio formats only (no ffmpeg needed).
"""

import os
import requests
import logging
import yt_dlp

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YoutubeAPIKey", "")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# yt-dlp options — no download, no ffmpeg, audio only pre-muxed
YDL_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio[acodec=aac]/bestaudio",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
    "no_check_certificate": True,
    "socket_timeout": 10,
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    # Extractor args to reduce bot detection
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"],
        }
    },
}


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


def _ytdlp_extract(video_id: str):
    """
    Use yt-dlp to extract a direct audio stream URL.
    No download, no ffmpeg — just URL extraction.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                logger.error("yt-dlp returned no info")
                return None

            stream_url = info.get("url")
            if stream_url:
                logger.info(f"yt-dlp got URL: {stream_url[:80]}")
                return stream_url

            # Some formats nest the URL inside formats list
            formats = info.get("formats", [])
            for f in reversed(formats):
                furl = f.get("url", "")
                ext = f.get("ext", "")
                acodec = f.get("acodec", "none")
                vcodec = f.get("vcodec", "none")
                # Audio only, prefer m4a/mp3/aac
                if acodec != "none" and vcodec == "none" and furl:
                    logger.info(f"yt-dlp format: ext={ext} acodec={acodec}")
                    return furl

            logger.error("yt-dlp: no usable audio URL found in formats")
            return None

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp DownloadError: {e}")
        return None
    except Exception as e:
        logger.error(f"yt-dlp error: {e}", exc_info=True)
        return None


def get_youtube_stream(query: str):
    """
    Returns (stream_url, title, None) or (None, None, None).
    Flow: YouTube API v3 search → yt-dlp URL extraction
    """
    video_id, title = _youtube_search(query)
    if not video_id:
        return None, None, None

    stream_url = _ytdlp_extract(video_id)
    if stream_url:
        return stream_url, title, None

    logger.error(f"yt-dlp failed for: {title} ({video_id})")
    return None, None, None

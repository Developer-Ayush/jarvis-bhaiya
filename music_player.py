"""
music_player.py  –  Jarvis Alexa Skill
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uses yt-dlp (Python library) to extract a direct HTTPS audio stream
URL from YouTube — NO ADS, NO BROWSER, NO FFMPEG DOWNLOAD.

How it works
────────────
  1. yt-dlp searches YouTube for the song name.
  2. It extracts the best audio-only format (m4a/AAC preferred,
     fallback to best available audio).
  3. The raw HTTPS stream URL is returned to the Alexa AudioPlayer,
     which streams it directly to the Echo device.
  4. Since we bypass the YouTube webpage / player entirely,
     there are zero ads — no pre-roll, no mid-roll, nothing.

Alexa-compatible audio formats
───────────────────────────────
  • AAC / M4A  ← preferred (high quality, small size)
  • MP3        ← fallback
  • Opus       ← NOT supported by Alexa (skipped)
  • WebM       ← NOT supported by Alexa (skipped)

Lambda /tmp usage
──────────────────
  yt-dlp writes its cache to /tmp (Lambda's only writable path).
"""

import os
import logging
import yt_dlp

logger = logging.getLogger(__name__)

_CACHE_DIR = "/tmp/yt-dlp-cache"
os.makedirs(_CACHE_DIR, exist_ok=True)

# Formats Alexa's AudioPlayer can actually play
_ALEXA_OK_EXTS = {"m4a", "mp3", "aac", "mp4"}

# ──────────────────────────────────────────────────────────────
# yt-dlp options
# ──────────────────────────────────────────────────────────────

def _build_ydl_opts() -> dict:
    return {
        # Prefer AAC/M4A audio-only → best quality Alexa can play
        "format": "bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio[ext=mp3]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cachedir": _CACHE_DIR,
        # Do NOT download; just extract info
        "skip_download": True,
        # Age gate bypass (some music videos)
        "age_limit": None,
        # Avoid rate limiting
        "sleep_interval": 0,
        "max_sleep_interval": 0,
    }


# ──────────────────────────────────────────────────────────────
# Main function
# ──────────────────────────────────────────────────────────────

def get_youtube_stream(query: str) -> tuple[str | None, str | None, str | None]:
    """
    Search YouTube for `query` and return:
        (stream_url, title, thumbnail_url)

    Returns (None, None, None) if nothing is found or an error occurs.

    Parameters
    ──────────
    query : str
        Song name or search string, e.g. "Sahiba", "Tum Hi Ho Arijit Singh"
    """
    logger.info(f"Searching YouTube for: {query}")

    search_query = f"ytsearch1:{query}"          # Search, pick top result
    ydl_opts = _build_ydl_opts()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        if not info:
            logger.warning(f"No info returned for query: {query}")
            return None, None, None

        # ytsearch wraps results in 'entries'
        entries = info.get("entries")
        if entries:
            video = entries[0]
        else:
            video = info          # Direct URL was passed

        if not video:
            return None, None, None

        title     = video.get("title", query)
        thumbnail = video.get("thumbnail", "")
        formats   = video.get("formats", [])

        logger.info(f"Found: '{title}' — scanning {len(formats)} formats")

        # ── Pick best Alexa-compatible audio-only format ────────
        best_url   = None
        best_abr   = 0      # audio bitrate

        for fmt in formats:
            ext     = fmt.get("ext", "")
            acodec  = fmt.get("acodec", "none")
            vcodec  = fmt.get("vcodec", "none")
            abr     = fmt.get("abr") or 0
            url     = fmt.get("url", "")

            # Must have audio, no video, Alexa-ok extension
            if (acodec != "none"
                    and vcodec == "none"
                    and ext in _ALEXA_OK_EXTS
                    and url):
                if abr > best_abr:
                    best_abr = abr
                    best_url = url

        # Fallback: any audio-only format regardless of extension
        if not best_url:
            for fmt in formats:
                acodec = fmt.get("acodec", "none")
                vcodec = fmt.get("vcodec", "none")
                url    = fmt.get("url", "")
                abr    = fmt.get("abr") or 0
                if acodec != "none" and vcodec == "none" and url:
                    if abr > best_abr:
                        best_abr = abr
                        best_url = url

        # Last resort: video URL (Alexa can sometimes handle it)
        if not best_url:
            best_url = video.get("url")

        if best_url:
            logger.info(f"Stream URL obtained for '{title}' at {best_abr} kbps")
        else:
            logger.warning(f"No usable stream URL found for '{title}'")

        return best_url, title, thumbnail

    except yt_dlp.utils.DownloadError as de:
        logger.error(f"yt-dlp DownloadError: {de}")
        return None, None, None
    except Exception as exc:
        logger.error(f"Unexpected error in get_youtube_stream: {exc}", exc_info=True)
        return None, None, None

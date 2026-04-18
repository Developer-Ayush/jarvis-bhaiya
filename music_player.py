import requests
import logging

logger = logging.getLogger(__name__)

# Public Piped API instances - uses YouTube content directly
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.projectsegfau.lt",
    "https://pipedapi.bocchi.rocks",
]

def _get_working_instance():
    """Find a working Piped instance."""
    for instance in PIPED_INSTANCES:
        try:
            r = requests.get(f"{instance}/trending", timeout=5)
            if r.status_code == 200:
                return instance
        except:
            continue
    return PIPED_INSTANCES[0]


def get_youtube_stream(query: str):
    """
    Search YouTube via Piped API and return direct audio stream URL.
    No bot detection. Real YouTube content. No API key needed.
    """
    try:
        logger.info(f"Searching YouTube (via Piped) for: {query}")
        instance = _get_working_instance()
        logger.info(f"Using Piped instance: {instance}")

        # Step 1 — Search YouTube
        search_url = f"{instance}/search"
        params = {"q": query, "filter": "music_songs"}
        headers = {"User-Agent": "Mozilla/5.0"}

        search_resp = requests.get(
            search_url, params=params,
            headers=headers, timeout=10
        )

        if search_resp.status_code != 200:
            logger.error(f"Search failed: {search_resp.status_code}")
            return None, None, None

        search_data = search_resp.json()
        items = search_data.get("items", [])

        if not items:
            logger.warning(f"No results for: {query}")
            return None, None, None

        # Step 2 — Get first result video ID
        first = items[0]
        video_url = first.get("url", "")        # e.g. /watch?v=abc123
        title     = first.get("title", query)
        thumbnail = first.get("thumbnail", "")
        video_id  = video_url.replace("/watch?v=", "").strip()

        logger.info(f"Found: {title} | ID: {video_id}")

        # Step 3 — Get stream URL from Piped
        stream_resp = requests.get(
            f"{instance}/streams/{video_id}",
            headers=headers, timeout=10
        )

        if stream_resp.status_code != 200:
            logger.error(f"Stream fetch failed: {stream_resp.status_code}")
            return None, None, None

        stream_data = stream_resp.json()
        audio_streams = stream_data.get("audioStreams", [])

        if not audio_streams:
            logger.warning(f"No audio streams for: {title}")
            return None, None, None

        # Step 4 — Pick best quality audio stream Alexa can play
        # Alexa supports: mp4a (AAC), mp3
        # Sort by bitrate descending
        audio_streams.sort(
            key=lambda x: x.get("bitrate", 0), reverse=True
        )

        stream_url = None
        for stream in audio_streams:
            mime = stream.get("mimeType", "")
            url  = stream.get("url", "")
            if ("mp4" in mime or "mp3" in mime or "aac" in mime) and url:
                stream_url = url
                logger.info(
                    f"Selected stream: {mime} "
                    f"@ {stream.get('bitrate', '?')} bps"
                )
                break

        # Fallback — just take the first one
        if not stream_url and audio_streams:
            stream_url = audio_streams[0].get("url")

        if stream_url:
            logger.info(f"Stream URL obtained for: {title}")
            return stream_url, title, thumbnail
        else:
            logger.warning(f"No usable stream URL for: {title}")
            return None, None, None

    except Exception as exc:
        logger.error(f"Piped error: {exc}", exc_info=True)
        return None, None, None

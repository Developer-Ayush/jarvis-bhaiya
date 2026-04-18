import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
app = Flask(__name__)

errors = []

try:
    from chatbot import ChatBot
except Exception as e:
    errors.append(f"chatbot: {e}")

try:
    from model import FirstLayerDMM
except Exception as e:
    errors.append(f"model: {e}")

try:
    from realtime_search import RealtimeSearchEngine
except Exception as e:
    errors.append(f"realtime_search: {e}")

try:
    from automation import handle_automation
except Exception as e:
    errors.append(f"automation: {e}")

try:
    from music_player import get_youtube_stream
except Exception as e:
    errors.append(f"music_player: {e}")

try:
    from ask_sdk_core.skill_builder import SkillBuilder
    from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler
except Exception as e:
    errors.append(f"ask_sdk: {e}")

@app.route("/debug-music", methods=["GET"])
def debug_music():
    import requests as req
    song = __import__('flask').request.args.get("song", "Sahiba")
    result = {}

    # Step 1: Check API key
    yt_key = os.environ.get("YoutubeAPIKey", "")
    result["youtube_key_set"] = bool(yt_key)
    result["youtube_key_preview"] = yt_key[:8] + "..." if yt_key else "MISSING"

    # Step 2: Try YouTube search
    if yt_key:
        try:
            r = req.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": song, "type": "video",
                        "maxResults": 1, "key": yt_key},
                timeout=8,
            )
            result["youtube_api_status"] = r.status_code
            if r.status_code == 200:
                items = r.json().get("items", [])
                if items:
                    result["video_id"] = items[0]["id"]["videoId"]
                    result["video_title"] = items[0]["snippet"]["title"]
                else:
                    result["youtube_error"] = "No items returned"
            else:
                result["youtube_error"] = r.text[:200]
        except Exception as e:
            result["youtube_exception"] = str(e)

    # Step 3: Try each Piped instance
    video_id = result.get("video_id")
    if video_id:
        piped_results = {}
        for instance in [
            "https://pipedapi.kavin.rocks",
            "https://api.piped.projectsegfau.lt",
            "https://pipedapi.bocchi.rocks",
            "https://piped-api.garudalinux.org",
        ]:
            try:
                r = req.get(f"{instance}/streams/{video_id}", timeout=8)
                piped_results[instance] = {
                    "status": r.status_code,
                    "streams": len(r.json().get("audioStreams", [])) if r.status_code == 200 else 0
                }
            except Exception as e:
                piped_results[instance] = {"error": str(e)}
        result["piped"] = piped_results

    return __import__('flask').jsonify(result)

@app.route("/", methods=["GET"])
def health():
    if errors:
        return jsonify({"status": "import errors", "errors": errors}), 500
    return jsonify({"status": "ok", "message": "All imports successful!"})

@app.route("/test-music", methods=["GET"])
def test_music():
    if errors:
        return jsonify({"status": "import errors", "errors": errors}), 500
    from music_player import get_youtube_stream
    song = __import__('flask').request.args.get("song", "Sahiba")
    url, title, _ = get_youtube_stream(song)
    if url:
        return jsonify({"status": "ok", "title": title, "url": url})
    return jsonify({"status": "error", "message": "Stream not found"}), 500

application = app
handler = app

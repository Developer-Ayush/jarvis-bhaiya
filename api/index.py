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

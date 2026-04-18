"""
api/index.py — Jarvis AI Alexa Skill (Vercel entry point)
Diagnostic version — wraps all imports in try/except to expose exact crash.
"""

import sys
import os
import logging
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Collect import errors instead of crashing ──────────────────────────────────
IMPORT_ERRORS = {}

try:
    from flask import Flask, request, jsonify, Response as FlaskResponse
except Exception as e:
    IMPORT_ERRORS["flask"] = traceback.format_exc()

try:
    from ask_sdk_core.skill_builder import SkillBuilder
    from ask_sdk_core.handler_input import HandlerInput
    from ask_sdk_core.utils import is_request_type, is_intent_name
    from ask_sdk_model import Response
    from ask_sdk_model.interfaces.audioplayer import (
        PlayDirective, PlayBehavior, AudioItem, Stream,
    )
    from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler
except Exception as e:
    IMPORT_ERRORS["ask_sdk"] = traceback.format_exc()

try:
    from chatbot import ChatBot
except Exception as e:
    IMPORT_ERRORS["chatbot"] = traceback.format_exc()

try:
    from model import FirstLayerDMM
except Exception as e:
    IMPORT_ERRORS["model"] = traceback.format_exc()

try:
    from realtime_search import RealtimeSearchEngine
except Exception as e:
    IMPORT_ERRORS["realtime_search"] = traceback.format_exc()

try:
    from automation import handle_automation
except Exception as e:
    IMPORT_ERRORS["automation"] = traceback.format_exc()

try:
    from music_player import get_youtube_stream
except Exception as e:
    IMPORT_ERRORS["music_player"] = traceback.format_exc()

# Log all import errors at startup so they appear in Vercel logs
for module, err in IMPORT_ERRORS.items():
    logger.error(f"IMPORT FAILED [{module}]:\n{err}")

USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")

app = Flask(__name__)


# ── Health check — shows import errors if any ──────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    if IMPORT_ERRORS:
        modules = ", ".join(IMPORT_ERRORS.keys())
        return f"❌ Import errors in: {modules}. Check /debug for details.", 500
    return f"✅ {ASSISTANT_NAME} AI skill is running! Endpoint: /alexa"


# ── Debug endpoint — shows full tracebacks ─────────────────────────────────────
@app.route("/debug", methods=["GET"])
def debug():
    if not IMPORT_ERRORS:
        return jsonify({"status": "ok", "message": "All imports succeeded!"})
    return jsonify({"status": "error", "import_errors": IMPORT_ERRORS}), 500


# ── Only build Alexa skill if all imports succeeded ────────────────────────────
if not IMPORT_ERRORS:
    sb = SkillBuilder()

    @sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
    def launch_handler(handler_input: HandlerInput) -> Response:
        speech = f"Namaste {USERNAME}! Main {ASSISTANT_NAME} hoon. Kya seva kar sakta hoon?"
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("Haan boliye, main sun raha hoon.")
            .response
        )

    @sb.request_handler(can_handle_func=is_intent_name("MusicPlayIntent"))
    def music_handler(handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        song  = slots["song"].value if slots.get("song") else None
        if not song:
            return (
                handler_input.response_builder
                .speak("Kaun sa gana bajana hai?")
                .ask("Song ka naam batao.")
                .response
            )
        stream_url, title, _ = get_youtube_stream(song)
        if not stream_url:
            return (
                handler_input.response_builder
                .speak(f"Sorry {USERNAME}, {song} abhi nahi chal pa raha.")
                .ask("Koi aur gana batao?")
                .response
            )
        return (
            handler_input.response_builder
            .speak(f"Bajata hoon {title}.")
            .add_directive(
                PlayDirective(
                    play_behavior=PlayBehavior.REPLACE_ALL,
                    audio_item=AudioItem(
                        stream=Stream(
                            token=title,
                            url=stream_url,
                            offset_in_milliseconds=0,
                        )
                    ),
                )
            )
            .set_should_end_session(True)
            .response
        )

    @sb.request_handler(can_handle_func=is_intent_name("QueryIntent"))
    def query_handler(handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        query = slots["query"].value if slots.get("query") else None
        if not query:
            return (
                handler_input.response_builder
                .speak("Kya jaanna chahte hain?")
                .ask("Batao.")
                .response
            )

        auto = handle_automation(query.lower())
        if auto:
            return handler_input.response_builder.speak(auto).ask("Aur kuch?").response

        decisions = FirstLayerDMM(query)
        answer = ""

        for d in decisions:
            if d.startswith("play "):
                song = d.removeprefix("play ").strip()
                stream_url, title, _ = get_youtube_stream(song)
                if stream_url:
                    return (
                        handler_input.response_builder
                        .speak(f"Bajata hoon {title}.")
                        .add_directive(
                            PlayDirective(
                                play_behavior=PlayBehavior.REPLACE_ALL,
                                audio_item=AudioItem(
                                    stream=Stream(
                                        token=title,
                                        url=stream_url,
                                        offset_in_milliseconds=0,
                                    )
                                ),
                            )
                        )
                        .set_should_end_session(True)
                        .response
                    )
                answer = f"Sorry {USERNAME}, {song} nahi chal pa raha abhi."
            elif d.startswith("realtime "):
                answer = RealtimeSearchEngine(d.removeprefix("realtime ").strip())
            elif d.startswith("general "):
                answer = ChatBot(d.removeprefix("general ").strip())
            elif d == "exit":
                return (
                    handler_input.response_builder
                    .speak(f"Alvida {USERNAME}! Take care.")
                    .set_should_end_session(True)
                    .response
                )
            else:
                answer = ChatBot(query)

        return (
            handler_input.response_builder
            .speak(answer or "Samajh nahi aaya, dobara boliye.")
            .ask("Aur kuch?")
            .response
        )

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.PauseIntent"))
    def pause_handler(handler_input): return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.ResumeIntent"))
    def resume_handler(handler_input): return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.StopIntent"))
    def stop_handler(handler_input):
        return (
            handler_input.response_builder
            .speak(f"Theek hai {USERNAME}.")
            .set_should_end_session(True)
            .response
        )

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.CancelIntent"))
    def cancel_handler(handler_input):
        return handler_input.response_builder.set_should_end_session(True).response

    @sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
    def help_handler(handler_input):
        return (
            handler_input.response_builder
            .speak(f"Main {ASSISTANT_NAME} hoon. Gana bajao, ya kuch bhi poochho.")
            .ask("Kya help chahiye?")
            .response
        )

    @sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
    def session_ended_handler(handler_input):
        error = getattr(handler_input.request_envelope.request, "error", None)
        if error:
            logger.error(f"SessionEnded error: {error}")
        return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStarted"))
    def playback_started(handler_input): return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackFinished"))
    def playback_finished(handler_input): return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStopped"))
    def playback_stopped(handler_input): return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackFailed"))
    def playback_failed(handler_input):
        logger.error("AudioPlayer.PlaybackFailed")
        return handler_input.response_builder.response

    @sb.request_handler(can_handle_func=is_request_type("PlaybackController.PlayCommandIssued"))
    def playback_command(handler_input): return handler_input.response_builder.response

    @sb.exception_handler(can_handle_func=lambda i, e: True)
    def error_handler(handler_input, exception):
        logger.error(f"Skill error: {exception}", exc_info=True)
        return (
            handler_input.response_builder
            .speak("Kuch gadbad ho gayi. Dobara try karein.")
            .ask("Dobara boliye.")
            .response
        )

    skill_handler = WebserviceSkillHandler(
        skill=sb.create(),
        verify_signature=False,
        verify_timestamp=False,
    )

    @app.route("/alexa", methods=["POST"])
    def alexa_endpoint():
        try:
            response = skill_handler.verify_request_and_dispatch(
                http_headers=dict(request.headers),
                http_body=request.data.decode("utf-8"),
            )
            return FlaskResponse(response, content_type="application/json")
        except Exception as e:
            logger.error(f"Endpoint error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

else:
    # If imports failed, still handle /alexa so Alexa gets a response
    @app.route("/alexa", methods=["POST"])
    def alexa_endpoint():
        logger.error("Alexa request received but imports failed — check /debug")
        return jsonify({"error": "skill not loaded due to import errors"}), 500


# ── Test music ─────────────────────────────────────────────────────────────────
@app.route("/test-music", methods=["GET"])
def test_music():
    if "music_player" in IMPORT_ERRORS:
        return jsonify({"error": IMPORT_ERRORS["music_player"]}), 500
    song = request.args.get("song", "Sahiba")
    url, title, _ = get_youtube_stream(song)
    if url:
        return jsonify({"status": "ok", "title": title, "url": url})
    return jsonify({"status": "error", "message": "Stream not found"}), 500


# ── Vercel entry point ─────────────────────────────────────────────────────────
application = app
handler     = app

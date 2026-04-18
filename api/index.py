"""
api/index.py — Jarvis AI Alexa Skill (Vercel entry point)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from flask import Flask, request, jsonify, Response  # ← add Response
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import Response
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem, Stream
)
from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler

from chatbot import ChatBot
from model import FirstLayerDMM
from realtime_search import RealtimeSearchEngine
from automation import handle_automation
from music_player import get_youtube_stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")

app = Flask(__name__)
sb  = SkillBuilder()

# ── Health check ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return f"✅ {ASSISTANT_NAME} AI skill is running! Endpoint: /alexa"

# ── Test music ────────────────────────────────────────────────
@app.route("/test-music", methods=["GET"])
def test_music():
    song = request.args.get("song", "Sahiba")
    url, title, _ = get_youtube_stream(song)
    if url:
        return jsonify({"status": "ok", "title": title, "url": url})
    return jsonify({"status": "error", "message": "Stream not found"}), 500

# ── Launch ────────────────────────────────────────────────────
@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_handler(handler_input: HandlerInput) -> Response:
    speech = f"Namaste {USERNAME}! Main {ASSISTANT_NAME} hoon. Kya seva kar sakta hoon?"
    return (
        handler_input.response_builder
        .speak(speech)
        .ask("Haan boliye, main sun raha hoon.")
        .response
    )

# ── Music ─────────────────────────────────────────────────────
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
            .speak(f"Sorry, {song} abhi nahi chal pa raha.")
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

# ── Query ─────────────────────────────────────────────────────
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
            answer = f"Sorry, {song} nahi chal pa raha abhi."
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

# ── Control intents ───────────────────────────────────────────
@sb.request_handler(can_handle_func=is_intent_name("AMAZON.PauseIntent"))
def pause_handler(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.ResumeIntent"))
def resume_handler(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.StopIntent"))
def stop_handler(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.CancelIntent"))
def cancel_handler(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_handler(handler_input):
    return handler_input.response_builder.response

# ── Session ended (REQUIRED) ──────────────────────────────────
@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_handler(handler_input):
    return handler_input.response_builder.response

# ── AudioPlayer events ────────────────────────────────────────
@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStarted"))
def playback_started(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackFinished"))
def playback_finished(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackStopped"))
def playback_stopped(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_request_type("AudioPlayer.PlaybackFailed"))
def playback_failed(handler_input):
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_request_type("PlaybackController.PlayCommandIssued"))
def playback_command(handler_input):
    return handler_input.response_builder.response

# ── Error handler ─────────────────────────────────────────────
@sb.exception_handler(can_handle_func=lambda i, e: True)
def error_handler(handler_input, exception):
    logger.error(f"Alexa error: {exception}", exc_info=True)
    return (
        handler_input.response_builder
        .speak("Kuch gadbad ho gayi. Dobara try karein.")
        .response
    )

# ── Alexa POST endpoint ───────────────────────────────────────
skill_handler = WebserviceSkillHandler(
    skill=sb.create(),
    verify_signature=False,   # Vercel proxy mangles headers
    verify_timestamp=False,
)

@app.route("/alexa", methods=["POST"])
def alexa_endpoint():
    try:
        response = skill_handler.verify_request_and_dispatch(
            http_headers=dict(request.headers),
            http_body=request.data.decode("utf-8"),
        )
        return Response(response, content_type="application/json")  # ← fix
    except Exception as e:
        logger.error(f"Alexa endpoint error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ── Vercel entry point ────────────────────────────────────────
application = app
handler     = app

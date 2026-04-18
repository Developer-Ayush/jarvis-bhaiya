"""
api/index.py  —  Jarvis AI Alexa Skill
Runs as a Flask serverless function on Vercel (free, no card, always on).

Flow:
  "Alexa, Bhaiya, Sahiba gana chalado"
        ↓
   Vercel HTTPS endpoint  (this file)
        ↓
   Alexa SDK processes request
        ↓
   Matthew voice + ad-free YouTube music
"""

import sys
import os

# Make root-level modules importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_webservice_support.webservice_handler import WebServiceSkillHandler
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem,
    Stream, AudioItemMetadata, StopDirective,
)

from chatbot import ChatBot
from realtime_search import RealtimeSearchEngine
from model import FirstLayerDMM
from automation import handle_automation
from music_player import get_youtube_stream

# ─────────────────────────────────────────────
app = Flask(__name__)

ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")
USERNAME       = os.environ.get("Username", "Sir")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def matthew(text: str) -> str:
    text = text.replace("&", "and").replace("<", "").replace(">", "")
    return f'<speak><voice name="Matthew">{text}</voice></speak>'


def sanitise(text: str) -> str:
    import re
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"`+", "", text)
    return text.replace("</s>", "").strip()[:7500]


def process_decision(decision: list, original_query: str):
    """Returns (spoken_text, audio_url_or_None)"""
    R = any(i.startswith("realtime") for i in decision)
    merged = " and ".join(
        [" ".join(i.split()[1:]) for i in decision
         if i.startswith("general") or i.startswith("realtime")]
    )

    # Music
    for d in decision:
        if d.startswith("play "):
            song = d.removeprefix("play ").strip()
            url, title, _ = get_youtube_stream(song)
            if url:
                return f"Playing {title} for you {USERNAME}. Enjoy!", url
            return f"Sorry {USERNAME}, could not find {song}. Try another song.", None

    # Automation
    auto_funcs = ["google search", "youtube search", "content", "reminder"]
    auto_lines = []
    for d in decision:
        if any(d.startswith(f) for f in auto_funcs):
            r = handle_automation(d)
            if r:
                auto_lines.append(r)

    # Real-time
    if R:
        return sanitise(RealtimeSearchEngine(merged or original_query)), None

    # General
    for d in decision:
        if d.startswith("general "):
            return sanitise(ChatBot(d.replace("general ", "").strip())), None

    # Exit
    for d in decision:
        if d == "exit":
            return f"Goodbye {USERNAME}, have a great day!", None

    if auto_lines:
        return " ".join(auto_lines), None

    return sanitise(ChatBot(original_query)), None


# ─────────────────────────────────────────────
# REQUEST HANDLERS
# ─────────────────────────────────────────────

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak = matthew(
            f"Haan {USERNAME}! Main {ASSISTANT_NAME} hoon. "
            "Gana sunna ho toh song ka naam ke baad gana chalado kaho. "
            "Koi sawaal ho toh seedha pooch lo. Batao kya karna hai?"
        )
        return (
            handler_input.response_builder
            .speak(speak)
            .ask(matthew("Haan bolo."))
            .response
        )


class MusicPlayIntentHandler(AbstractRequestHandler):
    """Handles: 'Sahiba gana chalado', 'play Tum Hi Ho', etc."""
    def can_handle(self, handler_input):
        return is_intent_name("MusicPlayIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        song_slot = slots.get("song") if slots else None
        song = song_slot.value.strip() if song_slot and song_slot.value else None

        if not song:
            return (
                handler_input.response_builder
                .speak(matthew("Kaun sa gana bajana hai?"))
                .ask(matthew("Song ka naam batao."))
                .response
            )

        url, title, _ = get_youtube_stream(song)

        if not url:
            return (
                handler_input.response_builder
                .speak(matthew(
                    f"Sorry {USERNAME}, {song} nahi mila YouTube pe. "
                    "Koi aur gana try karo."
                ))
                .ask(matthew("Koi aur gana batao?"))
                .response
            )

        return (
            handler_input.response_builder
            .speak(matthew(f"Suno {USERNAME}, {title}!"))
            .add_directive(PlayDirective(
                play_behavior=PlayBehavior.REPLACE_ALL,
                audio_item=AudioItem(
                    stream=Stream(
                        token=f"jarvis::{title}",
                        url=url,
                        offset_in_milliseconds=0,
                    ),
                    metadata=AudioItemMetadata(
                        title=title,
                        subtitle=f"{ASSISTANT_NAME} AI — Ad Free",
                    ),
                ),
            ))
            .set_should_end_session(True)
            .response
        )


class QueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("QueryIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        q_slot = slots.get("query") if slots else None
        query = q_slot.value.strip() if q_slot and q_slot.value else None

        if not query:
            return (
                handler_input.response_builder
                .speak(matthew("Samjha nahi. Dobara poochho."))
                .ask(matthew("Kya poochna tha?"))
                .response
            )

        try:
            decision = FirstLayerDMM(query)
            spoken, audio_url = process_decision(decision, query)
        except Exception as e:
            spoken, audio_url = "Kuch problem ho gayi. Dobara try karo.", None

        if audio_url:
            return (
                handler_input.response_builder
                .speak(matthew(spoken))
                .add_directive(PlayDirective(
                    play_behavior=PlayBehavior.REPLACE_ALL,
                    audio_item=AudioItem(
                        stream=Stream(
                            token=f"jarvis::{query}",
                            url=audio_url,
                            offset_in_milliseconds=0,
                        ),
                        metadata=AudioItemMetadata(
                            title=query,
                            subtitle=f"{ASSISTANT_NAME} AI",
                        ),
                    ),
                ))
                .set_should_end_session(True)
                .response
            )

        return (
            handler_input.response_builder
            .speak(matthew(spoken))
            .ask(matthew("Aur kuch?"))
            .response
        )


class PauseIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.PauseIntent")(handler_input)

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .add_directive(StopDirective())
            .response
        )


class ResumeIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.ResumeIntent")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class StopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.StopIntent")(handler_input)
            or is_intent_name("AMAZON.CancelIntent")(handler_input)
        )

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .speak(matthew(f"Theek hai {USERNAME}, phir milenge!"))
            .add_directive(StopDirective())
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak = matthew(
            f"Main {ASSISTANT_NAME} hoon. Yeh kaam kar sakta hoon. "
            "Gana sunna ho toh song name ke baad gana chalado kaho — bilkul bina ads ke. "
            "Koi sawaal ho toh seedha pooch lo. "
            "Latest news ke liye poocho aaj ka news kya hai. "
            "Google search ke liye kaho Google pe search karo. "
            "Kuch likhwana ho toh kaho write karo. "
            f"Alexa, Bhaiya, Sahiba gana chalado — aise use karo {USERNAME}."
        )
        return (
            handler_input.response_builder
            .speak(speak)
            .ask(matthew("Batao kya karna hai?"))
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .speak(matthew("Samjha nahi. Help sunne ke liye kaho help."))
            .ask(matthew("Kya poochna tha?"))
            .response
        )


# AudioPlayer event handlers (required when AudioPlayer is enabled)
class AudioPlayerHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return handler_input.request_envelope.request.object_type.startswith("AudioPlayer.")

    def handle(self, handler_input):
        return handler_input.response_builder.response


class PlaybackControllerHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return handler_input.request_envelope.request.object_type.startswith("PlaybackController.")

    def handle(self, handler_input):
        return handler_input.response_builder.response


class SessionEndedHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        return (
            handler_input.response_builder
            .speak(matthew("Kuch gadbad ho gayi. Dobara try karo."))
            .ask(matthew("Dobara try karo."))
            .response
        )


# ─────────────────────────────────────────────
# BUILD SKILL
# ─────────────────────────────────────────────

sb = CustomSkillBuilder(api_client=DefaultApiClient())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(MusicPlayIntentHandler())
sb.add_request_handler(QueryIntentHandler())
sb.add_request_handler(PauseIntentHandler())
sb.add_request_handler(ResumeIntentHandler())
sb.add_request_handler(StopIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(AudioPlayerHandler())
sb.add_request_handler(PlaybackControllerHandler())
sb.add_request_handler(SessionEndedHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

skill = sb.create()

# ─────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────

@app.route("/alexa", methods=["POST"])
def alexa_endpoint():
    """Main endpoint Alexa calls. Paste this URL in your skill endpoint."""
    handler = WebServiceSkillHandler(
        skill=skill,
        verify_signature=False,   # Set True after testing
        verify_timestamp=False,   # Set True after testing
    )
    response = handler.verify_request_and_dispatch(
        http_api_headers=dict(request.headers),
        http_api_body=request.data.decode("utf-8"),
    )
    return jsonify(response)


@app.route("/", methods=["GET"])
def health():
    """Health check — open this URL to confirm deployment is live."""
    return f"✅ {ASSISTANT_NAME} AI skill is running on Vercel! Endpoint: /alexa", 200


# Vercel needs the app object exposed
# (Vercel auto-detects Flask apps)

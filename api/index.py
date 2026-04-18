import sys
import os
import logging
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, request, jsonify

app = Flask(__name__)

ASSISTANT_NAME = os.environ.get("AssistantName", "Bhaiya")
USERNAME       = os.environ.get("Username", "Sir")
GROQ_KEY       = os.environ.get("GroqAPIKey", "")
COHERE_KEY     = os.environ.get("CohereApiKey", "")


def matthew(text: str) -> str:
    text = text.replace("&", "and").replace("<", "").replace(">", "")
    return f'<speak><voice name="Matthew">{text}</voice></speak>'


def _build_response(text, end_session, reprompt=None, directives=None):
    response = {
        "outputSpeech": {"type": "SSML", "ssml": matthew(text)},
        "shouldEndSession": end_session
    }
    if reprompt:
        response["reprompt"] = {
            "outputSpeech": {"type": "SSML", "ssml": matthew(reprompt)}
        }
    if directives:
        response["directives"] = directives
    return jsonify({"version": "1.0", "response": response}), 200


def _build_audio_response(speak_text, stream_url, title):
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "SSML", "ssml": matthew(speak_text)},
            "directives": [{
                "type": "AudioPlayer.Play",
                "playBehavior": "REPLACE_ALL",
                "audioItem": {
                    "stream": {
                        "token": f"jarvis::{title}",
                        "url": stream_url,
                        "offsetInMilliseconds": 0
                    },
                    "metadata": {
                        "title": title,
                        "subtitle": f"{ASSISTANT_NAME} AI — Ad Free"
                    }
                }
            }],
            "shouldEndSession": True
        }
    }), 200


def _process_decision(decision, original_query):
    import re
    def clean(text):
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"#+\s*", "", text)
        text = re.sub(r"`+", "", text)
        return text.replace("</s>", "").strip()[:7000]

    R = any(i.startswith("realtime") for i in decision)
    merged = " and ".join(
        [" ".join(i.split()[1:]) for i in decision
         if i.startswith("general") or i.startswith("realtime")]
    )

    for d in decision:
        if d.startswith("play "):
            song = d.removeprefix("play ").strip()
            from music_player import get_youtube_stream
            url, title, _ = get_youtube_stream(song)
            if url:
                return f"Playing {title} for you {USERNAME}!", url
            return f"Sorry {USERNAME}, {song} nahi mila.", None

    auto_keys = ["google search", "youtube search", "content", "reminder"]
    for d in decision:
        if any(d.startswith(k) for k in auto_keys):
            from automation import handle_automation
            result = handle_automation(d)
            if result:
                return clean(result), None

    if R:
        from realtime_search import RealtimeSearchEngine
        return clean(RealtimeSearchEngine(merged or original_query)), None

    for d in decision:
        if d.startswith("general "):
            from chatbot import ChatBot
            return clean(ChatBot(d.replace("general ", "").strip())), None

    for d in decision:
        if d == "exit":
            return f"Goodbye {USERNAME}!", None

    from chatbot import ChatBot
    return clean(ChatBot(original_query)), None


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "assistant": ASSISTANT_NAME,
        "groq_key_set": bool(GROQ_KEY),
        "cohere_key_set": bool(COHERE_KEY),
        "endpoint": "/alexa"
    }), 200


@app.route("/alexa", methods=["POST"])
def alexa_endpoint():
    try:
        data = json.loads(request.data.decode("utf-8"))
        request_type = data.get("request", {}).get("type", "")
        intent_name  = data.get("request", {}).get("intent", {}).get("name", "")
        logger.info(f"Type: {request_type} | Intent: {intent_name}")

        if request_type == "LaunchRequest":
            return _build_response(
                f"Haan {USERNAME}! Main {ASSISTANT_NAME} hoon. "
                "Gana sunna ho toh song ka naam ke baad gana chalado kaho. "
                "Koi sawaal ho toh seedha pooch lo. Batao kya karna hai?",
                end_session=False,
                reprompt="Haan bolo."
            )

        elif request_type == "IntentRequest":

            if intent_name == "MusicPlayIntent":
                slots = data["request"]["intent"].get("slots", {})
                song  = slots.get("song", {}).get("value", "")
                if not song:
                    return _build_response(
                        "Kaun sa gana bajana hai?",
                        end_session=False,
                        reprompt="Song ka naam batao."
                    )
                from music_player import get_youtube_stream
                url, title, _ = get_youtube_stream(song)
                if url:
                    return _build_audio_response(f"Suno {USERNAME}, {title}!", url, title)
                return _build_response(
                    f"Sorry {USERNAME}, {song} nahi mila. Koi aur try karo.",
                    end_session=False, reprompt="Koi aur gana batao?"
                )

            elif intent_name == "QueryIntent":
                slots = data["request"]["intent"].get("slots", {})
                query = slots.get("query", {}).get("value", "")
                if not query:
                    return _build_response(
                        "Samjha nahi. Dobara poochho.",
                        end_session=False, reprompt="Kya poochna tha?"
                    )
                from model import FirstLayerDMM
                decision = FirstLayerDMM(query)
                logger.info(f"Decision: {decision}")
                spoken, audio_url = _process_decision(decision, query)
                if audio_url:
                    return _build_audio_response(spoken, audio_url, query)
                return _build_response(spoken, end_session=False, reprompt="Aur kuch?")

            elif intent_name == "AMAZON.PauseIntent":
                return jsonify({
                    "version": "1.0",
                    "response": {
                        "directives": [{"type": "AudioPlayer.Stop"}],
                        "shouldEndSession": True
                    }
                }), 200

            elif intent_name == "AMAZON.ResumeIntent":
                return jsonify({"version": "1.0", "response": {}}), 200

            elif intent_name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
                return _build_response(
                    f"Theek hai {USERNAME}, phir milenge!",
                    end_session=True,
                    directives=[{"type": "AudioPlayer.Stop"}]
                )

            elif intent_name == "AMAZON.HelpIntent":
                return _build_response(
                    f"Main {ASSISTANT_NAME} hoon. "
                    "Gana sunna ho toh song ke baad gana chalado kaho. "
                    "Koi sawaal pooch sakte ho. "
                    "News ke liye kaho aaj ka news kya hai. "
                    f"Try karo: Sahiba gana chalado. Batao {USERNAME}?",
                    end_session=False, reprompt="Batao kya karna hai?"
                )

            else:
                return _build_response(
                    "Samjha nahi. Help bolne ke liye kaho help.",
                    end_session=False, reprompt="Kya poochna tha?"
                )

        elif request_type == "SessionEndedRequest":
            return jsonify({"version": "1.0", "response": {}}), 200

        elif request_type.startswith("AudioPlayer.") or \
             request_type.startswith("PlaybackController."):
            return jsonify({"version": "1.0", "response": {}}), 200

        else:
            return _build_response(
                "Kuch samjha nahi. Dobara try karo.",
                end_session=False
            )

    except Exception as exc:
        logger.error(f"Error: {exc}", exc_info=True)
        return _build_response(
            f"Kuch gadbad ho gayi {USERNAME}. Dobara try karo.",
            end_session=False
        )

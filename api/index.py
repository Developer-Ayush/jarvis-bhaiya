from flask import Flask
import os

app = Flask(__name__)
errors = []

try:
    from ask_sdk_core.skill_builder import CustomSkillBuilder
    from ask_sdk_core.api_client import DefaultApiClient
    from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
    from ask_sdk_core.utils import is_request_type, is_intent_name
    from ask_sdk_core.handler_input import HandlerInput
    from ask_sdk_model import Response
except Exception as e:
    errors.append(f"ask_sdk_core: {e}")

try:
    from ask_sdk_webservice_support.webservice_handler import WebServiceSkillHandler
except Exception as e:
    errors.append(f"ask_sdk_webservice_support: {e}")

try:
    from ask_sdk_model.interfaces.audioplayer import (
        PlayDirective, PlayBehavior, AudioItem,
        Stream, AudioItemMetadata, StopDirective,
    )
except Exception as e:
    errors.append(f"ask_sdk_model.audioplayer: {e}")

try:
    import groq
except Exception as e:
    errors.append(f"groq: {e}")

try:
    import cohere
except Exception as e:
    errors.append(f"cohere: {e}")

try:
    import yt_dlp
except Exception as e:
    errors.append(f"yt_dlp: {e}")

try:
    from googlesearch import search
except Exception as e:
    errors.append(f"googlesearch: {e}")

@app.route("/", methods=["GET"])
def health():
    if errors:
        return "<br>".join(errors), 500
    return "✅ All packages load fine!", 200

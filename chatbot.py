"""
chatbot.py  –  Jarvis Alexa Skill
Stateless Groq LLM wrapper.  All responses are plain text;
Matthew SSML wrapping is done in lambda_function.py.
"""

import datetime
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")
GROQ_API_KEY   = os.environ.get("GroqAPIKey", "")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = f"""Hello, I am {USERNAME}.
You are {ASSISTANT_NAME}, an advanced AI assistant.
Rules:
- Keep answers CONCISE (3-5 sentences max) — they will be spoken aloud by Alexa.
- Use plain English. NO bullet points, NO markdown, NO special characters.
- Be professional, warm, and conversational.
- Address the user as {USERNAME} occasionally.
- Full stops, commas, and question marks only for punctuation."""

_session_messages: list = []


def _now_info() -> str:
    n = datetime.datetime.now()
    return (f"Current time info: {n.strftime('%A, %d %B %Y, %H:%M:%S')}.")


def _clean(text: str) -> str:
    lines = [l for l in text.split("\n") if l.strip()]
    return " ".join(lines).replace("</s>", "").strip()


def ChatBot(query: str) -> str:
    global _session_messages
    _session_messages.append({"role": "user", "content": query})

    system = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _now_info()},
    ]

    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=system + _session_messages,
            max_tokens=300,
            temperature=0.7,
            top_p=1,
            stream=True,
        )
        answer = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                answer += delta

        answer = _clean(answer)
        _session_messages.append({"role": "assistant", "content": answer})

        # Keep memory bounded (last 10 turns)
        if len(_session_messages) > 20:
            _session_messages = _session_messages[-20:]

        return answer

    except Exception as exc:
        logger.error(f"ChatBot error: {exc}", exc_info=True)
        _session_messages.pop()
        return "I am having trouble connecting right now. Please try again in a moment."

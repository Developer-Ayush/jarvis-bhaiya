"""
realtime_search.py  –  Jarvis Alexa Skill
Google search → Groq → concise spoken answer.
"""

import datetime
import os
import logging
from googlesearch import search
from groq import Groq

logger = logging.getLogger(__name__)

USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")
GROQ_API_KEY   = os.environ.get("GroqAPIKey", "")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, an advanced AI assistant.
Answer ONLY from the search data provided.
Rules:
- Maximum 4 sentences. Spoken aloud by Alexa — no lists, no markdown.
- Plain English, professional tone.
- If data is insufficient, say so briefly."""

_BASE_CHAT = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"},
]


def _google_search(query: str, num: int = 5) -> str:
    try:
        results = list(search(query, advanced=True, num_results=num))
    except Exception as exc:
        logger.warning(f"Google search error: {exc}")
        return f"Search results for '{query}' are unavailable right now."

    out = f"Search results for '{query}':\n[start]\n"
    for r in results:
        out += f"Title: {r.title}\nDescription: {r.description}\n\n"
    return out + "[end]"


def _now_info() -> str:
    n = datetime.datetime.now()
    return f"Current date and time: {n.strftime('%A, %d %B %Y, %H:%M:%S')}."


def _clean(text: str) -> str:
    lines = [l for l in text.split("\n") if l.strip()]
    return " ".join(lines).replace("</s>", "").strip()


def RealtimeSearchEngine(prompt: str) -> str:
    search_data = _google_search(prompt)

    messages = [{"role": "user", "content": prompt}]
    system_with_data = _BASE_CHAT + [
        {"role": "system", "content": search_data},
        {"role": "system", "content": _now_info()},
    ]

    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=system_with_data + messages,
            temperature=0.7,
            max_tokens=300,
            top_p=1,
            stream=True,
        )
        answer = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                answer += delta
        return _clean(answer)

    except Exception as exc:
        logger.error(f"RealtimeSearchEngine error: {exc}", exc_info=True)
        return "I could not fetch real-time information right now. Please try again."

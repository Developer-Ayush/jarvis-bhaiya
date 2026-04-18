"""
model.py  –  Jarvis Alexa Skill
Cohere command-r-plus decision model.
Updated preamble includes Hindi music commands.
"""

import os
import logging
import cohere

logger = logging.getLogger(__name__)

COHERE_API_KEY = os.environ.get("CohereApiKey", "")
co = cohere.Client(api_key=COHERE_API_KEY)

FUNCS = [
    "exit", "general", "realtime", "play",
    "google search", "youtube search",
    "content", "reminder", "generate image",
]

PREAMBLE = """
You are a Decision-Making Model. Classify the user's query into one of the categories below.
DO NOT answer the query — only classify it.

Categories:
-> 'general (query)'        — answerable by an LLM, no real-time data needed.
-> 'realtime (query)'       — needs current internet data (news, prices, who is X right now, etc.).
-> 'play (song name)'       — user wants to play/listen to a song. Also triggered by Hindi phrases:
                              'gana chalado', 'bajao', 'sunao', 'lagao', 'play karo', 'gana laga do'.
                              Example: 'Sahiba gana chalado' → 'play Sahiba'
                              Example: 'Tum Hi Ho bajao' → 'play Tum Hi Ho'
                              Example: 'play Shape of You' → 'play Shape of You'
-> 'google search (topic)'  — user wants to search Google.
-> 'youtube search (topic)' — user wants to search YouTube (NOT play, just search).
-> 'content (topic)'        — user wants written content: essay, email, code, poem, etc.
-> 'reminder (datetime msg)'— user wants a reminder set.
-> 'exit'                   — user says goodbye / wants to end the conversation.
-> 'general (query)'        — fallback for anything not listed above.

For multiple tasks, comma-separate: 'play Sahiba, general who sang Sahiba'
"""

CHAT_HISTORY = [
    {"role": "User",    "message": "how are you"},
    {"role": "Chatbot", "message": "general how are you"},
    {"role": "User",    "message": "Sahiba gana chalado"},
    {"role": "Chatbot", "message": "play Sahiba"},
    {"role": "User",    "message": "Tum Hi Ho bajao"},
    {"role": "Chatbot", "message": "play Tum Hi Ho"},
    {"role": "User",    "message": "play Shape of You"},
    {"role": "Chatbot", "message": "play Shape of You"},
    {"role": "User",    "message": "Arijit Singh ka gana sunao"},
    {"role": "Chatbot", "message": "play Arijit Singh"},
    {"role": "User",    "message": "aaj ka news kya hai"},
    {"role": "Chatbot", "message": "realtime today's news"},
    {"role": "User",    "message": "who is the PM of India"},
    {"role": "Chatbot", "message": "realtime who is the PM of India"},
    {"role": "User",    "message": "search google for best restaurants"},
    {"role": "Chatbot", "message": "google search best restaurants"},
    {"role": "User",    "message": "search youtube for lofi music"},
    {"role": "Chatbot", "message": "youtube search lofi music"},
    {"role": "User",    "message": "write an email to my boss"},
    {"role": "Chatbot", "message": "content email to boss"},
    {"role": "User",    "message": "bye"},
    {"role": "Chatbot", "message": "exit"},
]


def FirstLayerDMM(prompt: str) -> list:
    try:
        stream = co.chat_stream(
            model="command-r-plus",
            message=prompt,
            temperature=0.7,
            chat_history=CHAT_HISTORY,
            prompt_truncation="OFF",
            connectors=[],
            preamble=PREAMBLE,
        )
        response = ""
        for event in stream:
            if event.event_type == "text-generation":
                response += event.text

        response = response.replace("\n", "")
        parts = [p.strip() for p in response.split(",")]
        valid = [p for p in parts if any(p.startswith(f) for f in FUNCS)]

        if not valid or "(query)" in " ".join(valid):
            return [f"general {prompt}"]
        return valid

    except Exception as exc:
        logger.error(f"FirstLayerDMM error: {exc}", exc_info=True)
        return [f"general {prompt}"]

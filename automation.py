"""
automation.py  –  Jarvis Alexa Skill
Voice-only automations. Desktop commands are gracefully declined.
"""

import os
import logging
import requests
from googlesearch import search
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY   = os.environ.get("GroqAPIKey", "")
USERNAME       = os.environ.get("Username", "Sir")
ASSISTANT_NAME = os.environ.get("AssistantName", "Jarvis")

client = Groq(api_key=GROQ_API_KEY)


def _google_search_spoken(topic: str) -> str:
    try:
        results = list(search(topic, advanced=True, num_results=3))
        if not results:
            return f"I couldn't find any Google results for {topic}."
        answer = f"Here are the top Google results for {topic}. "
        for i, r in enumerate(results, 1):
            desc = r.description or ""
            answer += f"Result {i}: {r.title}. {desc}. "
        return answer.strip()
    except Exception as exc:
        logger.error(f"Google search error: {exc}")
        return f"I had trouble searching Google for {topic}."


def _youtube_search_spoken(topic: str) -> str:
    encoded = topic.replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={encoded}"
    return (
        f"I searched YouTube for {topic}. "
        f"The search link is: {url}. "
        "Check the Alexa app for the clickable link."
    )


def _content_writer(topic: str) -> str:
    system = [{"role": "system", "content": (
        "You are a professional content writer. "
        "Write what is requested in 100 words or less. "
        "Plain text only — no bullet points or markdown. "
        "It will be read aloud by Alexa."
    )}]
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=system + [{"role": "user", "content": topic}],
            max_tokens=200,
            temperature=0.7,
            stream=False,
        )
        return completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.error(f"Content writer error: {exc}")
        return f"I had trouble writing content about {topic}."


def _reminder_spoken(text: str) -> str:
    return (
        f"I'd like to set a reminder for {text}. "
        "However, setting reminders requires the Alexa Reminders permission. "
        "Please enable it in the Alexa app under skill permissions, then try again."
    )


def _image_not_supported() -> str:
    return (
        "Image generation is not available in the Alexa skill version, "
        "because Alexa has no screen. Please use the desktop version of Jarvis."
    )


def _desktop_not_supported(command: str) -> str:
    return (
        f"The command '{command}' is a desktop-only feature "
        "and is not available in the Alexa version of Jarvis."
    )


def handle_automation(command: str) -> str | None:
    command = command.strip()

    for prefix in ["open ", "close ", "system "]:
        if command.startswith(prefix):
            return _desktop_not_supported(command)

    if command.startswith("google search "):
        return _google_search_spoken(command.removeprefix("google search ").strip())

    if command.startswith("youtube search "):
        return _youtube_search_spoken(command.removeprefix("youtube search ").strip())

    if command.startswith("content "):
        return _content_writer(command.removeprefix("content ").strip())

    if command.startswith("reminder "):
        return _reminder_spoken(command.removeprefix("reminder ").strip())

    if command.startswith("generate image"):
        return _image_not_supported()

    return None   # Not an automation command

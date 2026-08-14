import os
import string
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import SYSTEM_PROMPT

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
client = genai.Client()

# Ordered smartest/newest first; each is tried in turn on rate limit or error.
MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
]

_QUESTION_WORDS = {
    "who",
    "what",
    "whats",
    "when",
    "where",
    "why",
    "how",
    "which",
    "whose",
    "whom",
}

# Imperative follow-ups (eg. "check for me" after Aigis offers to look
# something up) don't end in "?" or start with a question word, but still
# need grounding or the model has no way to actually fulfil them.
_LOOKUP_PHRASES = (
    "check",
    "look up",
    "look into",
    "look that up",
    "search",
    "find out",
    "google it",
    "tell me about",
)


def _system_instruction():
    now = datetime.now()
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Right now it's {now.strftime('%A, %B %d, %Y')}, "
        f"{now.strftime('%-I:%M %p')} (UK time, this server's clock)."
    )


def _looks_factual(message: str) -> bool:
    """Heuristic for whether a message is asking about real-world facts,
    so we only pay for search grounding when it's likely to help."""
    text = message.strip().lower()
    if not text:
        return False
    if text.endswith("?"):
        return True
    first_word = text.split(maxsplit=1)[0].strip(string.punctuation)
    if first_word in _QUESTION_WORDS:
        return True
    return any(phrase in text for phrase in _LOOKUP_PHRASES)


def _build_contents(conversation_context):
    """Turn (author, message) history into alternating user/model turns.

    conversation_context's last entry is always the message to respond to;
    passing it through structured turns (instead of flattening everything
    into one text blob) is what keeps the model from latching onto an
    earlier line in a long transcript instead of the actual latest message.
    """
    turns = []
    for name, msg in conversation_context:
        role = "model" if name == "Aigis" else "user"
        text = msg if role == "model" else f"{name}: {msg}"
        if turns and turns[-1].role == role:
            turns[-1].parts[0].text += f"\n{text}"
        else:
            turns.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return turns


def generate_content_llm(message, conversation_context):
    contents = _build_contents(conversation_context)
    print(f"[llm] Contents: {contents}")

    grounded = _looks_factual(message)
    system_instruction = _system_instruction()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[types.Tool(google_search=types.GoogleSearch())] if grounded else None,
    )
    if grounded:
        print("[llm] Looks like a factual question, enabling search grounding")

    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            if response and getattr(response, "text", None):
                return response.text.strip()
        except Exception as e:
            print(f"[llm] {model} failed: {e}")
            continue

    print("[llm] No available models to use!")
    return (
        "this idiot ran out of rate limits (or google didnt like what you typed). "
        "please pay us $1200 for ooomfieeee claudee roleplayyy~~~"
    )

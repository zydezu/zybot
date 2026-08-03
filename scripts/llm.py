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

BASE_CONFIG = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
GROUNDED_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[types.Tool(google_search=types.GoogleSearch())],
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
    return first_word in _QUESTION_WORDS


def generate_content_llm(message, author, conversation_context):
    context_formatted = "\n".join(
        f"{name}: {msg}" for name, msg in conversation_context
    )
    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""Today is {today}.

Recent conversation:
{context_formatted}

{author}: {message}

Respond to the above."""
    print(f"[llm] Prompt: {prompt}")

    grounded = _looks_factual(message)
    config = GROUNDED_CONFIG if grounded else BASE_CONFIG
    if grounded:
        print("[llm] Looks like a factual question, enabling search grounding")

    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
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

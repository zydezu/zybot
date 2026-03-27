import os

from dotenv import load_dotenv
from google import genai

from config import SYSTEM_PROMPT

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
client = genai.Client()

models = [
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemma-3-27b-it",
    "gemma-3-12b-it",
    "gemma-3-4b-it",
    "gemma-3-1b-it",
]


def generate_content_llm(message, author, conversation_context):
    context_formatted = "\n".join(
        f"{name}: {msg}" for name, msg in conversation_context[-15:]
    )
    prompt = f"""{SYSTEM_PROMPT}

Recent conversation:
{context_formatted}

{author}: {message}

Respond to the above."""
    print(f"[llm] Prompt: {prompt}")

    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            if response and getattr(response, "text", None):
                return response.text
        except Exception:
            continue

    print("[llm] No available models to use!")
    return (
        "this idiot ran out of rate limits (or google didnt like what you typed). "
        "please pay us $1200 for ooomfieeee claudee roleplayyy~~~"
    )

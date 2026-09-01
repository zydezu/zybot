import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
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

DEFAULT_TIMEZONE = "Europe/London"


def get_current_time(timezone: str = DEFAULT_TIMEZONE) -> str:
    """Get the current date and time in a given place.

    Call this whenever you're asked about the time or date somewhere other
    than here, or need to work out how long ago/until something is.

    Args:
        timezone: an IANA timezone name, eg. "Asia/Tokyo", "America/New_York",
            "Europe/London". Defaults to here (UK time) if omitted.
    """
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        return (
            f"'{timezone}' isn't a real timezone name, it needs to be an IANA "
            "name like 'Europe/London' or 'America/New_York'"
        )
    return now.strftime("%A, %B %d, %Y, %-I:%M %p %Z")


def get_server_status(server: str) -> str:
    """Get live metrics (CPU/RAM/disk/uptime/power draw) for one of zy's home servers.

    Args:
        server: which box to check, either "basil" or "sunny".
    """
    server = server.strip().lower()
    if server not in ("basil", "sunny"):
        return "no server called that, it's either 'basil' or 'sunny'"

    try:
        data = requests.get(f"https://status.boysare.moe/{server}", timeout=5).json()
    except Exception as e:
        return f"couldn't reach {server}'s metrics right now: {e}"

    uptime_days = data["uptime_s"] / 86400
    disks = ", ".join(
        f"{d['dev']} {d['used'] / 1024 / 1024:.0f}GB/{d['total'] / 1024 / 1024:.0f}GB ({d['pct']}%)"
        for d in data["disks"]
    )
    return (
        f"{server}: cpu {data['cpu']}%, ram {data['ram_used_mb']}MB/{data['ram_total_mb']}MB "
        f"({data['ram']}%), disks: {disks}, power draw {data['power_w']}W, "
        f"up {uptime_days:.1f} days"
    )


def _system_instruction():
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Right now it's {now.strftime('%A, %B %d, %Y')}, "
        f"{now.strftime('%-I:%M %p')} (UK time, this server's clock). "
        "You have tools to search the web, check the time anywhere else in "
        "the world, and check live metrics for zy's home servers (basil and "
        "sunny) — actually use them when a question depends on current or "
        "real information instead of guessing, but don't mention the tools "
        "themselves or that you looked something up."
    )


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

    # The API rejects any request whose history doesn't start on a user
    # turn. Once the rolling context window trims its oldest entry, that's
    # exactly a coin flip away from happening on every other message - every
    # such request silently failed on every model, which looked like broken
    # memory rather than one malformed request.
    while turns and turns[0].role == "model":
        turns.pop(0)

    return turns


def generate_content_llm(conversation_context):
    contents = _build_contents(conversation_context)
    if not contents:
        return "..."
    print(f"[llm] Contents: {contents}")

    system_instruction = _system_instruction()
    tools = [
        types.Tool(google_search=types.GoogleSearch()),
        get_current_time,
        get_server_status,
    ]

    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                ),
            )
            if response and getattr(response, "text", None):
                return response.text.strip()
        except Exception as e:
            print(f"[llm] {model} failed with tools: {e}")
            # Some fallback models (eg. the gemma ones) don't support search
            # grounding or function calling at all - give the model one more
            # try bare before writing it off entirely.
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    ),
                )
                if response and getattr(response, "text", None):
                    return response.text.strip()
            except Exception as e2:
                print(f"[llm] {model} failed without tools too: {e2}")
            continue

    print("[llm] No available models to use!")
    return (
        "this idiot ran out of rate limits (or google didnt like what you typed). "
        "please pay us $1200 for ooomfieeee claudee roleplayyy~~~"
    )

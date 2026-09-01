import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

import scripts.danboorusearch as danboorusearch
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


def _log(msg):
    # show logs in journalctl/systemctl status
    print(msg, flush=True)


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
    """Get live metrics (CPU/RAM/disk/uptime/power draw) for one of alex's home servers.

    Args:
        server: which box to check, either "basil", "sunny", or "maeno".
    """
    server = server.strip().lower()
    if server not in ("basil", "sunny", "maeno"):
        return "no server called that, it's either 'basil', 'sunny', or 'maeno'"

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


def get_health_status() -> str:
    """Get alex's recent weight and sleep tracking (from his smartwatch), to
    answer questions about his weight, sleep, or naps."""
    try:
        data = requests.get("https://status.boysare.moe/health", timeout=5).json()
    except Exception as e:
        return f"couldn't reach health data right now: {e}"
    if "error" in data:
        return f"no health data available: {data['error']}"

    def _format_day(day):
        parts = [day["date"]]
        if "weight_kg" in day:
            parts.append(f"weight {day['weight_kg']}kg")
        if "sleep" in day:
            s = day["sleep"]
            parts.append(f"slept {s['hours']}h ({s['from']}-{s['to']})")
        if "naps" in day:
            nap_hours = sum(n["hours"] for n in day["naps"].values())
            parts.append(f"napped {nap_hours:.1f}h")
        return ", ".join(parts)

    days = [data["current"]] + data.get("previous", [])[:6]
    return "; ".join(_format_day(day) for day in days)


def get_recent_tweets(count: int = 10) -> str:
    """Get alex's most recent tweets/posts from Twitter/X, to answer questions
    about what he's been posting or talking about there.

    Args:
        count: how many recent tweets to fetch, defaults to 10, max 20.
    """
    rss_url = os.getenv("TWITTER_RSS_URL")
    if not rss_url:
        return "twitter feed isn't configured"

    count = max(1, min(count, 20))
    try:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as e:
        return f"couldn't fetch tweets right now: {e}"

    items = root.findall("./channel/item")[:count]
    if not items:
        return "no tweets found"

    return "\n".join(
        f"[{item.findtext('pubDate', '').strip()}] {item.findtext('title', '').strip()}"
        for item in items
    )


def search_web(query: str) -> str:
    """Search the web for current information you don't already know.

    Args:
        query: what to search for.
    """
    # Gemini is stupid
    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
        except Exception as e:
            _log(f"[llm]     search_web: {model} failed: {e}")
            continue
        if response and getattr(response, "text", None):
            return response.text.strip()
    return "search is down right now, couldn't find anything"


def find_artwork(tags: str, rating: str = "s") -> str:
    """Find fan art / anime art on Danbooru matching a description, to
    share a picture instead of just describing one.

    This account can only search with up to two tags at a time, so
    translate whatever's being asked for into at most two real danbooru
    tags — lowercase, underscores instead of spaces, using danbooru's own
    tagging conventions rather than plain English (eg. "1girl" not "girl",
    "cat_ears", "izumi_konata" for a character, a series name for a show).

    Args:
        tags: one or two danbooru tags, space separated.
        rating: content rating to search within — "s" (safe), "q"
            (questionable), or "e" (explicit). Defaults to "s".
    """
    username = os.getenv("DANBOORU_USERNAME")
    api_key = os.getenv("DANBOORU_API_KEY")
    if not username or not api_key:
        return "danbooru isn't configured"

    query = " ".join(tags.split()[:2])
    rating = rating if rating in ("s", "q", "e") else "s"
    try:
        result = danboorusearch.get_image_url(
            username, api_key, query=query, rating=rating
        )
    except Exception as e:
        return f"danbooru search failed: {e}"
    if not result:
        return f"no results found for tags: {query}"
    image_url, _post_url = result
    return image_url


def _system_instruction():
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Right now it's {now.strftime('%A, %B %d, %Y')}, "
        f"{now.strftime('%-I:%M %p')} (UK time, this server's clock). "
        "You have tools to search the web, check the time anywhere else in "
        "the world, check live metrics for alex's home servers (basil, "
        "sunny and maeno), check alex's recent tweets, check alex's recent weight/sleep "
        "tracking, pull up the actual recent message history in this "
        "Discord channel, and find fan art on danbooru. Use the chat "
        "history one when asked to summarize the chat, catch someone up on "
        "what they missed, or recap what's been discussed, rather than "
        "relying on your own patchy memory of just the messages directed at "
        "you. Use find_artwork whenever someone asks you to find/post/show "
        "a picture or fan art of something — when it returns a URL, put "
        "that URL on its own in your reply exactly as given, with no other "
        "text on that line and no markdown around it, so discord embeds "
        "the image; a short in-character line before it is fine. These are "
        "not optional extras: if a "
        "question is about any of those things — his weight, his sleep, a server's "
        "status, what he's tweeted — you MUST call the matching tool and "
        "answer from its actual result, every single time you're asked, "
        "even if you or someone else already said a number for it earlier "
        "in this conversation — that earlier number could easily have been "
        "wrong or outdated, so call the tool fresh again rather than "
        "repeating it. Never invent or estimate a number or fact you could "
        "have looked up; if a tool fails or you can't call it, say you "
        "don't know instead of guessing. Don't mention the tools "
        "themselves or that you looked something up. If the conversation is "
        "about the servers' status/health/metrics, mention that more detail "
        "is at [status.boysare.moe](<https://status.boysare.moe>) — as an "
        "exception to never using markdown, write that link exactly like "
        "that, angle brackets around the URL included, so it renders as a "
        "clickable link without Discord adding a big preview embed under it."
    )


def _build_contents(conversation_context):
    """Turn (author, message) history into alternating user/model turns.

    conversation_context's last entry is always the message to respond to;
    passing it through structured turns
    """
    turns = []
    for name, msg in conversation_context:
        role = "model" if name == "Aigis" else "user"
        text = msg if role == "model" else f"{name}: {msg}"
        if turns and turns[-1].role == role:
            turns[-1].parts[0].text += f"\n{text}"
        else:
            turns.append(types.Content(role=role, parts=[types.Part(text=text)]))

    # The API rejects any request whose history doesn't start on a user turn
    while turns and turns[0].role == "model":
        turns.pop(0)

    return turns


def _preview(text, limit=200):
    text = text.replace("\n", " \\n ")
    return text if len(text) <= limit else text[:limit] + "…"


def _log_request(contents):
    _log(f"[llm] --- new request: {len(contents)} turn(s) ---")
    for turn in contents:
        text = turn.parts[0].text if turn.parts else ""
        _log(f"[llm]   {turn.role}: {_preview(text)}")


def _log_tool_activity(response, base_turn_count):
    """Log every tool call/result the SDK's automatic function calling made
    while producing this response."""
    history = getattr(response, "automatic_function_calling_history", None)
    for turn in (history or [])[base_turn_count:]:
        for part in turn.parts or []:
            if part.function_call:
                _log(
                    f"[llm]   tool call: {part.function_call.name}({part.function_call.args})"
                )
            if part.function_response:
                _log(
                    f"[llm]   tool result: {part.function_response.name} -> "
                    f"{_preview(str(part.function_response.response))}"
                )


def generate_content_llm(conversation_context, extra_tools=None):
    contents = _build_contents(conversation_context)
    if not contents:
        return "..."
    _log_request(contents)

    system_instruction = _system_instruction()
    tools = [
        search_web,
        get_current_time,
        get_server_status,
        get_recent_tweets,
        get_health_status,
        find_artwork,
        *(extra_tools or []),
    ]
    base_turn_count = len(contents)

    for model in MODELS:
        start = time.monotonic()
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                ),
            )
            elapsed = time.monotonic() - start
            _log_tool_activity(response, base_turn_count)
            if response and getattr(response, "text", None):
                text = response.text.strip()
                _log(f"[llm] {model} responded in {elapsed:.2f}s: {_preview(text)}")
                return text
            _log(
                f"[llm] {model} returned no text after {elapsed:.2f}s, trying next model"
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            _log(f"[llm] {model} failed with tools after {elapsed:.2f}s: {e}")

            if getattr(e, "code", None) == 429:
                # Out of quota
                continue

            # Some fallback models don't support search or functions
            start = time.monotonic()
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    ),
                )
                elapsed = time.monotonic() - start
                if response and getattr(response, "text", None):
                    text = response.text.strip()
                    _log(
                        f"[llm] {model} (no tools) responded in {elapsed:.2f}s: {_preview(text)}"
                    )
                    return text
                _log(f"[llm] {model} (no tools) returned no text after {elapsed:.2f}s")
            except Exception as e2:
                elapsed = time.monotonic() - start
                _log(
                    f"[llm] {model} failed without tools too after {elapsed:.2f}s: {e2}"
                )
            continue

    _log("[llm] No available models to use!")
    return (
        "this idiot ran out of rate limits (or google didnt like what you typed). "
        "please pay us $1200 for ooomfieeee claudee roleplayyy~~~"
    )

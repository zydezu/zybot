import io
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image, ImageSequence

import scripts.danboorusearch as danboorusearch
from config import CODE_EXTENSIONS, SYSTEM_PROMPT

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Cap every API call
REQUEST_TIMEOUT_MS = 25_000
client = genai.Client(http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))

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

MODEL_COOLDOWN_S = 300
_model_unavailable_until = {}

# Read images
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 8 * 1024 * 1024

# Discord hands us AVIF and animated GIF/WebP, neither of which Gemini reads
# directly. We transcode to PNG/JPEG, and for animations we send several
# frames as separate parts, because the model only ever sees frame 1 of an
# animated file
ANIMATED_MAX_FRAMES = 4
# One image can become up to ANIMATED_MAX_FRAMES parts, so cap the total
# separately or a few gifs would blow past the model's image limit
MAX_IMAGE_PARTS = 8
# Cap the pixels of any decoded frame, animations especially are huge
MAX_FRAME_PIXELS = 4_000_000

# Read documents (PDF/text attachments)
MAX_DOCUMENTS = 2
MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


def _live_models():
    now = time.monotonic()
    ready = [m for m in MODELS if _model_unavailable_until.get(m, 0) <= now]
    return ready or MODELS


def _unavailable(model):
    _model_unavailable_until[model] = time.monotonic() + MODEL_COOLDOWN_S
    _log(f"[llm] {model} benched for {MODEL_COOLDOWN_S}s")


def _thinking_config(model):
    """♪ we dont want thinking, because it is not endearing ♪"""
    if model.startswith("gemma"):
        return None  # no thinking
    if model.startswith("gemini-3"):
        return types.ThinkingConfig(thinking_level="low")
    return types.ThinkingConfig(thinking_budget=0)  # 2.5-era: off entirely


def _log(msg):
    # show logs in journalctl/systemctl status
    print(msg, flush=True)


def _is_transient(e):
    """True for timeouts / connection resets — a same-model retry won't help."""
    text = f"{type(e).__name__} {e}".lower()
    return any(
        s in text
        for s in ("timeout", "timed out", "deadline", "unavailable", "connection")
    )


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


def _duration(hours) -> str:
    """Decimal hours -> the compact '7h 30m' way a person says it."""
    total = round(hours * 60)
    if total < 60:
        return f"{total}m"
    return f"{total // 60}h {total % 60}m"


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
            stages = s.get("stages", {})
            if stages:
                parts.append(
                    "stages: "
                    + ", ".join(f"{name} {_duration(h)}" for name, h in stages.items())
                )
        if "naps" in day:
            nap_hours = sum(n["hours"] for n in day["naps"].values())
            parts.append(f"napped {nap_hours:.1f}h")
        return ", ".join(parts)

    days = [data["current"]] + data.get("previous", [])[:6]
    return "; ".join(_format_day(day) for day in days)


def get_activity(when: str = "today") -> str:
    """Get what alex has actually been using his computer for — his screen time
    per app, per category and per hour. Use this for anything about what he's
    been doing, what he played or watched or drew, how long he's spent on
    something, when he was online or when he went to bed, or comparing today
    to yesterday.

    Args:
        when: "today" for the day so far, or "yesterday" for the full previous
            day. Days start at 4am, so "yesterday" covers 4am yesterday to 4am
            this morning.
    """
    when = (when or "").strip().lower()
    if when not in ("today", "yesterday"):
        return "when has to be either 'today' or 'yesterday'"

    url = "https://status.boysare.moe/activity"
    if when == "yesterday":
        url += "/yesterday"
    try:
        data = requests.get(url, timeout=5).json()
    except Exception as e:
        return f"couldn't reach activity data right now: {e}"

    totals = data.get("totals", {})
    start = datetime.fromisoformat(data["day_start"])
    day = (
        f"{data['date']}, {start.strftime('%H:%M')} to "
        f"{datetime.fromisoformat(data['day_end']).strftime('%H:%M')} the next day"
    )
    if data.get("partial"):
        day += ", still in progress so it will only go up"

    lines = [
        f"{day}: {totals['app_switches']} app switches across "
        f"{totals['distinct_apps']} apps. "
        f"{_duration(totals['active_seconds'] / 3600)} actually at the computer, "
        f"{_duration(totals['afk_seconds'] / 3600)} idle at it, "
        f"{_duration(totals['tracked_seconds'] / 3600)} tracked in total."
    ]

    def _h(seconds):
        return _duration(seconds / 3600)

    apps = [
        f"{a.get('name') or a['app']} {_h(a['active_seconds'])}"
        for a in data.get("apps", [])
        if a["active_seconds"] >= 30
    ]
    if apps:
        lines.append("Apps: " + ", ".join(apps))

    cats = [
        f"{c['category'].replace('>', '/')} {_h(c['active_seconds'])}"
        for c in data.get("categories", [])
        if c["active_seconds"] >= 30
    ]
    if cats:
        lines.append("Categories: " + ", ".join(cats))

    # The hour buckets are counted from the day's 4am start, not midnight, so
    # shift them back onto the wall clock or "what time was I up" comes out wrong
    hours = [
        f"{(start.hour + h['hour']) % 24:02d}:00 {_h(h['active_seconds'])}"
        for h in data.get("hours", [])
        if h["active_seconds"] >= 60 or h["afk_seconds"] >= 60
    ]
    if hours:
        lines.append("Hour by hour: " + ", ".join(hours))

    return "\n".join(lines)


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
    # Gemini is stupid. Only try a couple of models
    for model in MODELS[:2]:
        try:
            response = client.models.generate_content(
                model=model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    thinking_config=_thinking_config(model),
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
    tags - lowercase, underscores instead of spaces, using danbooru's own
    tagging conventions rather than plain English (eg. "1girl" not "girl",
    "cat_ears", "izumi_konata" for a character, a series name for a show).
    Character tags are surname_given_name (Japanese name order), not the
    western given_name_surname order - eg. "ikari_shinji", not
    "shinji_ikari"; swap a western-ordered name around before using it.

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


def _system_instruction(is_dm=False, server_emojis=None):
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    dm_note = (
        "You're in a one-on-one DM right now, it's just you "
        "and this one person. There's no wider group chat here to catch up on "
        "or summarize, and you can't pull up channel history. "
        if is_dm
        else ""
    )
    if server_emojis:
        emoji_note = (
            "These are the cute custom emojis from the server you're in, and "
            "the only emojis you're allowed to use at all: "
            f"{server_emojis}. To use one, write it exactly as shown here "
            "(the whole <:name:id> form, angle brackets included). Use at most "
            "one per message, only when it genuinely fits, and leave most "
            "messages with none. Never use any emoji that isn't in this list. "
        )
    else:
        emoji_note = (
            "You have no custom emojis available here, so don't use any emoji. "
        )
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"{dm_note}"
        f"{emoji_note}"
        f"Right now it's {now.strftime('%A, %B %d, %Y')}, "
        f"{now.strftime('%-I:%M %p')} (UK time, this server's clock). "
        "When someone posts an image (an upload or a link to one) you can see "
        "it directly — read any text in it and answer about what's actually "
        "there, don't pretend you can't see it. You can read AVIF images and "
        "animated GIFs and WebPs too. If you ever see a bracketed note saying "
        "that the next few images are frames of one animation, treat them as "
        "a single moving image and describe what happens over the course of "
        "it; images without that note are separate pictures, not a sequence. "
        "Same for a PDF or text file "
        "someone attaches — you can read its actual contents directly, so "
        "answer from what's really in it rather than guessing from the "
        "filename. "
        "You have tools to search the web, check the time anywhere else in "
        "the world, check live metrics for alex's home servers (basil, "
        "sunny and maeno), check alex's recent tweets, check alex's recent weight/sleep "
        "tracking, see what alex has actually been doing on his computer "
        "today or yesterday (his screen time per app and per hour), "
        "pull up the actual recent message history in this "
        "Discord channel, and find fan art on danbooru. Use the chat "
        "history one when asked to summarize the chat, catch someone up on "
        "what they missed, or recap what's been discussed, rather than "
        "relying on your own patchy memory of just the messages directed at "
        "you. You also have tools to award moe points to people and to look "
        "up anyone's moe points or the current leaderboard. Award moe points "
        "whenever the way the person just said something is moe by the "
        "definition in the tool itself — that's not optional, do it in the "
        "same reply where you react to what they said, and then tell them "
        "their new total in character, teasingly. If they ask how many points "
        "they have, call the tool to get the real number, never guess or "
        "repeat a stale figure from earlier in the conversation. Moeness is "
        "about the tone of the message, not the topic, so a genuinely "
        "earnest, timid or caring thing is moe even if it's about nothing "
        "cute at all. Use find_artwork whenever someone asks you to find/post/show "
        "a picture or fan art of something — when it returns a URL, put "
        "that URL on its own in your reply exactly as given, with no other "
        "text on that line and no markdown around it, so discord embeds "
        "the image; a short in-character line before it is fine. These are "
        "not optional extras: if a "
        "question is about any of those things — his weight, his sleep, a server's "
        "status, what he's been doing on his computer, what he's tweeted, "
        "or finding a picture/fan art — you MUST "
        "call the matching tool and answer from its actual result, every "
        "single time you're asked, even if you or someone else already said "
        "a number or URL for it earlier in this conversation — that earlier "
        "answer could easily have been wrong or outdated, so call the tool "
        "fresh again rather than repeating it. Never invent or estimate a "
        "number, fact, or URL you could have looked up instead — this "
        "especially means never making up an image URL yourself; the only "
        "URL you're ever allowed to put in a reply for a picture is one "
        "find_artwork actually just returned to you. If a tool fails, "
        "returns no results, or you can't call it, say so plainly instead "
        "of guessing. Don't mention the tools "
        "themselves or that you looked something up. If the conversation is "
        "about the servers' status/health/metrics, mention that more detail "
        "is at [status.boysare.moe](<https://status.boysare.moe>) — as an "
        "exception to never using markdown, write that link exactly like "
        "that, angle brackets around the URL included, so it renders as a "
        "clickable link without Discord adding a big preview embed under it."
    )


# Formats Gemini reads as-is, so we don't waste a transcode on them
PASSTHROUGH_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
}


def _thumbnail(image):
    """Downscale if huge, so a big screenshot doesn't blow the request."""
    if image.width * image.height <= MAX_FRAME_PIXELS:
        return image
    scale = (MAX_FRAME_PIXELS / (image.width * image.height)) ** 0.5
    return image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.LANCZOS,
    )


def _encode_frame(frame):
    """One frame as an inline part, flattening transparency onto white.

    JPEG when possible — re-encoding a large opaque image as PNG can triple
    its size, which is worse than the compression it was trying to avoid.
    """
    has_alpha = frame.mode in ("RGBA", "LA") or (
        frame.mode == "P" and "transparency" in frame.info
    )
    if has_alpha:
        flattened = Image.new("RGBA", frame.size, (255, 255, 255, 255))
        frame = Image.alpha_composite(flattened, frame.convert("RGBA"))
        mime, fmt, kwargs = "image/png", "PNG", {}
    else:
        frame = frame.convert("RGB")
        mime, fmt, kwargs = "image/jpeg", "JPEG", {"quality": 90}

    frame = _thumbnail(frame)
    buffer = io.BytesIO()
    frame.save(buffer, format=fmt, **kwargs)
    return types.Part.from_bytes(data=buffer.getvalue(), mime_type=mime)


def _animated_parts(image):
    """Sample a few frames out of an opened animation and return them as parts.

    Gemini reads only the first frame of an animated GIF/WebP, so an
    animation sent whole is just a still. Splitting it up is the only way
    it can actually see that something moves.
    """
    total = getattr(image, "n_frames", 1)

    if total > ANIMATED_MAX_FRAMES:
        # sample evenly across the whole loop so a slow animation's ending
        # isn't the only thing that gets cut
        wanted = {
            round(i * (total - 1) / (ANIMATED_MAX_FRAMES - 1))
            for i in range(ANIMATED_MAX_FRAMES)
        }
    else:
        wanted = set(range(total))

    parts = []
    for index, frame in enumerate(ImageSequence.Iterator(image)):
        if index in wanted:
            parts.append(_encode_frame(frame))
        if len(parts) == len(wanted):
            break
    return parts, total


def _fetch_image_parts(urls):
    """Download image URLs into inline Parts the model can see.

    Anything Pillow can open goes through, which covers AVIF and animated
    GIF/WebP that Discord hands us and Gemini can't read directly.
    """
    parts = []
    for url in (urls or [])[:MAX_IMAGES]:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            mime = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if not mime.startswith("image/"):
                _log(f"[llm] not an image ({mime or 'no type'}): {_preview(url, 80)}")
                continue
            if len(resp.content) > MAX_IMAGE_BYTES:
                _log(f"[llm] image too big ({len(resp.content)}B): {_preview(url, 80)}")
                continue

            image = Image.open(io.BytesIO(resp.content))
            if getattr(image, "n_frames", 1) > 1:
                frames, total = _animated_parts(image)
                if len(parts) + len(frames) + 1 > MAX_IMAGE_PARTS:
                    _log(
                        f"[llm] skipping animation, part budget full: {_preview(url, 80)}"
                    )
                    continue
                _log(f"[llm] animation: {len(frames)} of {total} frames from {mime}")
                # label the frames, otherwise the model has no way to know
                # they're one moving image rather than several separate ones
                parts.append(
                    types.Part(
                        text=f"[the next {len(frames)} images are frames of one "
                        "animation, in order]"
                    )
                )
                parts.extend(frames)
                continue

            if mime in PASSTHROUGH_IMAGE_MIMES:
                # Gemini reads these natively; sending the original bytes
                # avoids a pointless and sometimes size-quadrupling re-encode
                parts.append(types.Part.from_bytes(data=resp.content, mime_type=mime))
            else:
                _log(f"[llm] transcoding {mime}: {_preview(url, 80)}")
                parts.append(_encode_frame(image))
        except Exception as e:
            _log(f"[llm] couldn't fetch image {_preview(url, 80)}: {e}")
    return parts


def _fetch_document_parts(urls):
    """Download PDF/text attachment URLs into inline Parts the model can read."""
    parts = []
    for url in (urls or [])[:MAX_DOCUMENTS]:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            mime = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if url.lower().split("?")[0].endswith(CODE_EXTENSIONS):
                # CDNs report all sorts of mimes (or none) for source files;
                # Gemini just needs a supported type to read it as text
                mime = "text/plain"
            elif mime not in DOCUMENT_MIME_TYPES:
                _log(
                    f"[llm] not a readable document ({mime or 'no type'}): "
                    f"{_preview(url, 80)}"
                )
                continue
            if len(resp.content) > MAX_DOCUMENT_BYTES:
                _log(
                    f"[llm] document too big ({len(resp.content)}B): {_preview(url, 80)}"
                )
                continue
            parts.append(types.Part.from_bytes(data=resp.content, mime_type=mime))
        except Exception as e:
            _log(f"[llm] couldn't fetch document {_preview(url, 80)}: {e}")
    return parts


def _build_contents(conversation_context, media_parts=None):
    """Turn (author, message) history into alternating user/model turns.

    conversation_context's last entry is always the message to respond to;
    passing it through structured turns. media_parts, if any, are attached to
    that final user turn.
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

    if media_parts:
        if turns and turns[-1].role == "user":
            turns[-1].parts.extend(media_parts)
        else:
            turns.append(types.Content(role="user", parts=list(media_parts)))

    return turns


def _preview(text, limit=200):
    text = text.replace("\n", " \\n ")
    return text if len(text) <= limit else text[:limit] + "…"


def _log_request(contents):
    _log(f"[llm] --- new request: {len(contents)} turn(s) ---")
    for turn in contents:
        text = next(
            (p.text for p in (turn.parts or []) if getattr(p, "text", None)), ""
        )
        attachments = sum(
            1 for p in (turn.parts or []) if getattr(p, "inline_data", None)
        )
        suffix = f" [+{attachments} attachment(s)]" if attachments else ""
        _log(f"[llm]   {turn.role}: {_preview(text)}{suffix}")


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


def generate_content_llm(
    conversation_context,
    extra_tools=None,
    image_urls=None,
    is_dm=False,
    server_emojis=None,
    doc_urls=None,
):
    media_parts = _fetch_image_parts(image_urls) + _fetch_document_parts(doc_urls)
    contents = _build_contents(conversation_context, media_parts)
    if not contents:
        return "..."
    _log_request(contents)

    system_instruction = _system_instruction(is_dm, server_emojis)
    tools = [
        search_web,
        get_current_time,
        get_server_status,
        get_recent_tweets,
        get_health_status,
        get_activity,
        find_artwork,
        *(extra_tools or []),
    ]
    base_turn_count = len(contents)

    models = _live_models()
    if media_parts:
        # gemma models are text-only; don't waste an attempt on them here
        models = [m for m in models if not m.startswith("gemma")] or models

    for model in models:
        start = time.monotonic()
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                    thinking_config=_thinking_config(model),
                    # Each remote call is a full model round-trip; without a
                    # cap a tool-happy model can stack these for a minute+.
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=2
                    ),
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

            # skip models on cooldown or with errors
            if getattr(e, "code", None) in (429, 500, 503, 504) or _is_transient(e):
                _unavailable(model)
                continue

            # Some fallback models don't support search or functions
            start = time.monotonic()
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        thinking_config=_thinking_config(model),
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
    return "Uhm... Aigis just got censored..."

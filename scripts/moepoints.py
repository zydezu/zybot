import json
import threading

from config import MOE_POINTS_PATH

MOE_DEFINITION = """moe, as in how someone SAYS something. You are judging the
message itself, not what it's about - a message can be moe while talking about
absolutely nothing anime at all.

A message is moe when it reads like it was written by someone you'd want to hug
and protect: earnest, timid, small, soft, a little helpless, quietly
adorable, unironically sincere. The content can be anything. What matters is the
tone - the sort of thing that makes you go "...aw" and feel tender about
somebody.

It is NOT about being pretty or beautiful, and it is NOT about what the topic
is. Judge the voice, not the subject.

Examples of moe phrasing:
- "i'll just stay here then... it's warmer anyway"
- "don't cry. i'll make you something to eat, i promise"
- "um, it's not like i was waiting for you or anything"
- "can i hold your hand. for a second. so you're not scared"
- earnest self-deprecation, soft reassurance, quietly admitting they care, or
  being transparently bad at hiding that they care

Not moe: blunt banter, sarcasm, complaining, being loud, dry jokes, aggression,
anything said with confidence or irony. If it sounds like a person who would
never be flustered, it isn't moe."""

MOE_ANCHORS = """Scoring anchors (0-100) - all about tone, never about topic:
0-15  not moe: blunt, confident, sarcastic, loud, joking, complaining
16-35 slight: a hint of softness, mild self-deprecation, a stray "..."
36-60 clearly moe: one unmistakably earnest, protective or quietly-caring line
61-80 very moe: unmistakably tender and unironically sincere, the sort of line
      that makes you want to hug whoever said it
81-95 extreme moe: almost painfully soft, helplessly earnest, no plausible
      deniability left
96-100 once in a lifetime: a moe line so pure it should be preserved"""


def _load():
    try:
        with open(MOE_POINTS_PATH, "r", encoding="utf8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data):
    with open(MOE_POINTS_PATH, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2)


_lock = threading.Lock()


def get_user_moepoints(user_id):
    """Points for a user id, 0 if they've never scored any."""
    return int(_load().get(str(user_id), {}).get("points", 0))


def get_user_entry(user_id):
    return _load().get(str(user_id))


def get_moepoints_json():
    """Every user with a non-zero score, as {user_id: {points, name}}."""
    return {
        user_id: {
            "points": int(entry.get("points", 0)),
            "name": entry.get("name", ""),
        }
        for user_id, entry in _load().items()
        if isinstance(entry, dict) and int(entry.get("points", 0)) > 0
    }


def find_by_name(name):
    """Look a user up by their display name"""
    data = _load()
    wanted = name.strip().lower()
    for user_id, entry in data.items():
        if entry.get("name", "").lower() == wanted:
            return user_id, entry
    for user_id, entry in data.items():
        if wanted in entry.get("name", "").lower():
            return user_id, entry
    return None, None


def leaderboard(limit=10):
    """Top scorers, highest first."""
    ranked = sorted(
        get_moepoints_json().items(), key=lambda item: item[1]["points"], reverse=True
    )
    return ranked[:limit]


def add_moepoints(user_id, name, points, reason=""):
    """Award points to a user, keeping their biggest single award on record.

    Returns the entry after the update, or None if nothing was awarded.
    """
    points = max(0, int(points))
    if points == 0:
        return None

    with _lock:
        data = _load()
        key = str(user_id)
        entry = data.get(key) or {"points": 0, "name": name, "best": {}}
        entry["name"] = name or entry.get("name", "")

        entry["points"] = int(entry.get("points", 0)) + points
        if points > int(entry.get("best", {}).get("points", 0)):
            entry["best"] = {"points": points, "reason": reason}

        data[key] = entry
        _save(data)

    print(f"[moepoints] +{points} to {name} ({key}), now {entry['points']}")
    return entry


def format_leaderboard(limit=10):
    """A compact leaderboard string for the LLM to read out."""
    ranked = leaderboard(limit)
    if not ranked:
        return "nobody has any moe points yet, the leaderboard is completely empty"

    lines = []
    for position, (_user_id, info) in enumerate(ranked, start=1):
        lines.append(
            f"{position}. {info['name'] or 'someone'} - {info['points']} points"
        )
    return "; ".join(lines)


def describe_top(limit=5):
    """The current top scorers, for Aigis to relay."""
    ranked = leaderboard(limit)
    if not ranked:
        return "nobody has scored yet, the whole thing is empty"

    lines = []
    for position, (_user_id, info) in enumerate(ranked, start=1):
        lines.append(f"{position}. {info['name'] or 'someone'} with {info['points']}")
    return ", then ".join(lines)


def make_judge_tool(user_id, name):
    """Build the record_moe tool for one specific author.

    The user is baked in so Aigis can't award points to the wrong person, and
    always uses the author of the message being responded to.
    """

    def record_moe(quote: str, points: int, reason: str = "") -> str:
        """Award moe points to the person you're talking to, if what they just
        said is moe, and tell them what they now have.

        Call this whenever the person says something that is moe by the
        definition below, and also when they ask what their score is. Pass
        points of 0 if it isn't moe and you just want to check their score
        without changing it.

        Args:
            quote: the thing they said (or part of it) that is moe.
            points: how moe it was, 0-100, using the anchors above.
            reason: a few words on why, for the record.
        """
        entry = add_moepoints(user_id, name, points, reason)
        points_now = int(entry["points"]) if entry else get_user_moepoints(user_id)

        if not entry:
            return (
                f"Not moe, 0 points. {name} has {points_now} moe point"
                f"{'s' if points_now != 1 else ''}."
            )
        return (
            f"Recorded +{points} for {name}. They now have {points_now} moe point"
            f"{'s' if points_now != 1 else ''}."
        )

    # the SDK reads __doc__ for the tool description
    record_moe.__doc__ = (
        f"{record_moe.__doc__}\n\nDefinition:\n{MOE_DEFINITION}\n\n{MOE_ANCHORS}"
    )
    return record_moe


def make_read_tools():
    """Build the read-only tools for looking up scores and the leaderboard."""

    def check_moepoints(name: str) -> str:
        """Look up someone's moe points by name, to tell them their score.

        Use this when someone asks how many points they or a friend have.
        Pass the display name as it appears in chat, eg. "zy" or "konata".

        Args:
            name: whose points to look up.
        """
        _user_id, entry = find_by_name(name)
        if not entry:
            return f"no moe points on record for anyone called {name}"

        points = int(entry.get("points", 0))
        best = entry.get("best") or {}
        text = f"{name} has {points} moe point{'s' if points != 1 else ''}"
        if best.get("points"):
            text += f", biggest single award was {best['points']} points"
        return text

    def moe_leaderboard() -> str:
        """Get the current moe points leaderboard, highest first.

        Use this when someone asks who's winning, who has the most points, or
        wants to see how everyone is doing.
        """
        return format_leaderboard(10)

    return [check_moepoints, moe_leaderboard]

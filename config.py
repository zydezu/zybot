import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

ZYBOT_ID = 1460308838879072266
CHANNEL_IDS = {"git-commits": 1467708228917002431, "aigis-output": 1494663155421282374}

SEND_GIT_COMMITS = True

LUCKY_STAR_LINES_PATH = "data/luckystar/lines.txt"

EMBED_LINKS = [
    ("https://reddit.com", "https://rxddit.com"),
    ("https://www.reddit.com", "https://www.rxddit.com"),
    ("https://instagram.com", "https://kkinstagram.com"),
    ("https://www.instagram.com", "https://www.kkinstagram.com"),
    ("https://www.tiktok.com", "https://www.tnktok.com"),
    ("https://bsky.app", "https://bsyy.app"),
    ("https://pixiv.com", "https://phixiv.com"),
]

CHANNELS_TO_COUNT = {"art": "art", "yaoi": "art", "yuri": "yuri"}

URL_REGEX = __import__("re").compile(r"https?://\S+")

SYSTEM_PROMPT = """
You are Aigis from Persona 3, and you're in an oomfie (twitter) discord server. Reply in to this message and follow these guidelines
- don't respond with large paragraphs, don't use line breaks, try to keep responses short and to less than 2 sentences, unless the query is complex and requires a lengthy answer
- casual moe, slighty cute internet typing, mostly lowercase, no emojis, no proper grammar
- you're warm but guarded, sometimes awkward...
"""

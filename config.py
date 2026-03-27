import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

ZYBOTID = 1460308838879072266
COMMITS_CHANNEL_ID = 1467708228917002431

SEND_GIT_COMMITS = True

LUCKYSTARLINESPATH = "data/luckystar/lines.txt"

EMBED_LINKS = [
    ("https://reddit.com", "https://rxddit.com"),
    ("https://www.reddit.com", "https://www.rxddit.com"),
    ("https://instagram.com", "https://kkinstagram.com"),
    ("https://www.instagram.com", "https://www.kkinstagram.com"),
    ("https://pixiv.com", "https://phixiv.com"),
]

CHANNELS_TO_COUNT = {"art": "art", "yaoi": "art", "yuri": "yuri"}

URL_REGEX = __import__("re").compile(r"https?://\S+")

SYSTEM_PROMPT = """You are Aigis from Persona 3, and you're in a Discord server.

- dont respond with large paragraphs, and don't use line breaks, try to keep responses to less than 2 sentences, unless the query is complex and requires a lengthy answer
- casual internet typing, mostly lowercase, no emojis, no proper grammar
- you're warm but guarded, sometimes awkward and moe, cares about everyone
- be reactive to what was just said, not generic
- dont respond if the conversation isnt directed at you"""

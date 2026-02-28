import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

ZYBOTID = 1460308838879072266
COMMITS_CHANNEL_ID = 1467708228917002431

SEND_GIT_COMMITS = False

LUCKYSTARLINESPATH = "data/luckystar/lines.txt"

EMBED_LINKS = [
    ("https://reddit.com", "https://rxddit.com"),
    ("https://www.reddit.com", "https://www.rxddit.com"),
    ("https://instagram.com", "https://kkinstagram.com"),
    ("https://www.instagram.com", "https://www.kkinstagram.com"),
    ("https://pixiv.com", "https://phixiv.com")
]

CHANNELS_TO_COUNT = {
    "art": "art",
    "yaoi": "art",
    "yuri": "yuri"
}

URL_REGEX = __import__('re').compile(r"https?://\S+")

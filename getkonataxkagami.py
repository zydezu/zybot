import os, random, requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://danbooru.donmai.us/posts.json"
SEARCH_TAGS = "izumi_konata hiiragi_kagami rating:s"
LIMIT = 15

params = {
    "tags": SEARCH_TAGS,
    "limit": LIMIT
}

def get_image_url():
    response = requests.get(URL, params=params, auth=(os.getenv('DANBOORU_LOGIN'), os.getenv('DANBOORU_API_KEY')))
    if response.status_code == 200:
        posts = response.json()
        if not posts:
            print("No posts found for that tag.")
        else:
            post = random.choice(posts) # pick random image
            return post['file_url']
    else:
        print(f"Error: {response.status_code}")
    return
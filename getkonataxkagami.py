import random, requests

URL = "https://danbooru.donmai.us/posts.json"
SEARCH_TAGS = "izumi_konata hiiragi_kagami rating:s"
LIMIT = 200

params = {
    "tags": SEARCH_TAGS,
    "limit": LIMIT
}

def get_image_url(danbooru_login, danbooru_api_key):
    response = requests.get(URL, params=params, auth=(danbooru_login, danbooru_api_key))
    if response.status_code == 200:
        posts = response.json()
        if not posts:
            print("[getkonataxkagami] No posts found for that tag.")
        else:
            post = random.choice(posts)
            return post['file_url']
    else:
        print(f"[getkonataxkagami] Error: {response.status_code}")
    return
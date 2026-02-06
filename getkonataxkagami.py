import random, requests

URL = "https://danbooru.donmai.us/posts.json"
SEARCH_TAGS = "izumi_konata hiiragi_kagami rating:s"
LIMIT = 200

params = {
    "tags": SEARCH_TAGS,
    "limit": LIMIT
}

def get_image_url(danbooru_login, danbooru_api_key, query=None, rating=None):
    if query:
        search_tags = query
        if rating:
            search_tags += f" rating:{rating}"
    else:
        search_tags = SEARCH_TAGS
        if rating:
            search_tags += f" rating:{rating}"
    
    params = {
        "tags": search_tags,
        "limit": LIMIT
    }
    
    response = requests.get(URL, params=params, auth=(danbooru_login, danbooru_api_key))
    if response.status_code == 200:
        posts = response.json()
        if not posts:
            print(f"[getkonataxkagami] No posts found for query: {search_tags}")
        else:
            post = random.choice(posts)
            return post['file_url']
    else:
        print(f"[getkonataxkagami] Error: {response.status_code}")
    return
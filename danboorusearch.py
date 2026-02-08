import random, requests
from danbooru_tag_expander import TagExpander

URL = "https://danbooru.donmai.us/posts.json"
SEARCH_TAGS = "izumi_konata hiiragi_kagami rating:s"
LIMIT = 200

params = {
    "tags": SEARCH_TAGS,
    "limit": LIMIT
}

def tag_exists(tag, username, api_key):
    url = "https://danbooru.donmai.us/tags.json"
    params = {
        "search[name_matches]": tag,
        "limit": 1
    }

    r = requests.get(url, params=params, auth=(username, api_key))
    r.raise_for_status()
    data = r.json()

    return len(data) > 0

def get_image_url(danbooru_username, danbooru_api_key, query=None, rating=None):
    if query:
        tags = query.split()

        expander = TagExpander(
            use_cache=True,
            cache_dir="tag_cache"
        )

        resolved_tags = []

        for tag in tags:
            if tag_exists(tag, danbooru_username, danbooru_api_key):
                resolved_tags.append(tag)
            else:
                expander.expand_tags([tag])
                aliases = expander.get_aliases(tag)

                if aliases:
                    resolved_tags.extend(aliases)
                else:
                    resolved_tags.append(tag)

        search_tags = " ".join(resolved_tags)

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
    
    response = requests.get(URL, params=params, auth=(danbooru_username, danbooru_api_key))
    if response.status_code == 200:
        posts = response.json()
        if not posts:
            print(f"[danboorusearch] No posts found for query: {search_tags}")
        else:
            # Filter posts that have file_url
            valid_posts = [post for post in posts if 'file_url' in post and post['file_url']]
            if not valid_posts:
                print(f"[danboorusearch] No valid posts with file_url found for query: {search_tags}")
                return
            post = random.choice(valid_posts)
            return post['file_url']
    else:
        print(f"[danboorusearch] Error: {response.status_code}")
    return
import random

import requests
from danbooru_tag_expander import TagExpander

URL = "https://danbooru.donmai.us/posts.json"
SEARCH_TAGS = "izumi_konata hiiragi_kagami rating:s"
LIMIT = 200

BLOCKED_ARTISTS = ["setsuna22", "lasterk"]
ANIMATED_EXTENSIONS = (".gif", ".mp4", ".webm")

HEADERS = {"User-Agent": "zybot/1.0 (zydezu)"}


def _get(url, params, username, api_key):
    return requests.get(url, params=params, auth=(username, api_key), headers=HEADERS)


def upload_to_catbox(url):
    response = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "urlupload", "url": url},
        headers=HEADERS,
        timeout=120,
    )
    if response.status_code == 200 and response.text.strip().startswith("https://"):
        return response.text.strip()
    print(f"[danboorusearch] Catbox upload failed: {response.status_code} {response.text[:100]}")
    return url


def tag_exists(tag, username, api_key):
    url = "https://danbooru.donmai.us/tags.json"
    params = {"search[name_matches]": tag, "limit": 1}

    r = _get(url, params, username, api_key)
    r.raise_for_status()
    data = r.json()

    return len(data) > 0


def get_image_url(danbooru_username, danbooru_api_key, query=None, rating=None):
    if query:
        tags = query.split()

        expander = TagExpander(use_cache=True, cache_dir="data/tag_cache")

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

    params = {"tags": search_tags, "limit": LIMIT}

    response = _get(URL, params, danbooru_username, danbooru_api_key)
    if response.status_code == 200:
        posts = response.json()
        if not posts:
            print(f"[danboorusearch] No posts found for query: {search_tags}")
        else:
            # Filter posts that have file_url and don't contain blocked artists
            valid_posts = [
                post
                for post in posts
                if "file_url" in post
                and post["file_url"]
                and not any(artist in post["file_url"] for artist in BLOCKED_ARTISTS)
            ]
            if not valid_posts:
                print(
                    f"[danboorusearch] No valid posts with file_url found for query: {search_tags}"
                )
                return
            post = random.choice(valid_posts)
            file_url = post["file_url"]
            if any(file_url.lower().endswith(ext) for ext in ANIMATED_EXTENSIONS):
                print(f"[danboorusearch] Uploading animated media to catbox: {file_url}")
                file_url = upload_to_catbox(file_url)
            post_url = f"https://danbooru.donmai.us/posts/{post['id']}"
            return file_url, post_url
    else:
        print(f"[danboorusearch] Error {response.status_code}: {response.text[:200]}")
    return

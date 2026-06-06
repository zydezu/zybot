import os

import requests

import embed

SEEN_FILE = "data/seencommits.txt"
SEEN_REPOS_FILE = "data/seenrepos.txt"
SEEN_RELEASES_FILE = "data/seenreleases.txt"


def load_seen(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {line.strip() for line in f}


def save_seen(path, items):
    with open(path, "w") as f:
        f.writelines(f"{item}\n" for item in items)


def get_repos(github_username, headers):
    url = f"https://api.github.com/users/{github_username}/repos"
    return requests.get(url, headers=headers).json()


def get_commits(owner, repo_name, headers):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    commits = requests.get(url, headers=headers).json()
    if not isinstance(commits, list):
        return []
    return [
        {
            "repo": repo_name,
            "sha": commit["sha"],
            "author": commit["commit"]["author"]["name"],
            "message": commit["commit"]["message"],
            "url": commit["html_url"],
            "date": commit["commit"]["author"]["date"],
        }
        for commit in commits
    ]


def get_commit_stats(owner, repo_name, sha, headers):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{sha}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None, None
    stats = response.json().get("stats", {})
    return stats.get("additions", 0), stats.get("deletions", 0)


def get_releases(owner, repo_name, headers):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/releases"
    releases = requests.get(url, headers=headers).json()
    if not isinstance(releases, list):
        return []
    return [
        {
            "tag": r["tag_name"],
            "name": r.get("name") or r["tag_name"],
            "body": r.get("body") or "",
            "url": r["html_url"],
            "author": r["author"]["login"],
            "author_avatar_url": r["author"]["avatar_url"],
            "published_at": r["published_at"],
            "prerelease": r.get("prerelease", False),
        }
        for r in releases
        if not r.get("draft")
    ]


def get_org_repos(github_username, headers):
    orgs = requests.get(
        f"https://api.github.com/users/{github_username}/orgs", headers=headers
    ).json()
    org_repos = []
    for org in orgs:
        org_repos.extend(requests.get(org["repos_url"], headers=headers).json())
    return org_repos


def _process_repo(repo, owner, repo_id, headers, seen_repos, seen_releases,
                  new_shas, new_seen_repos, new_seen_releases,
                  new_commit_dicts, new_release_dicts, new_repo_embeds):
    repo_name = repo["name"]
    commits = get_commits(owner, repo_name, headers)

    # hacky way to stop the creation of forks flooding chat
    if repo_id not in seen_repos:
        for commit in commits:
            new_shas.add(commit["sha"])
        for release in get_releases(owner, repo_name, headers):
            if not release["prerelease"]:
                new_seen_releases.add(f"{repo_id}/{release['tag']}")
        new_seen_repos.add(repo_id)
        new_repo_embeds.append(
            embed.show_new_repo(
                repo_name,
                repo["owner"]["login"],
                repo["owner"]["avatar_url"],
                repo.get("html_url"),
                repo.get("fork"),
                repo.get("description"),
            )
        )
        return

    for commit in commits:
        sha = commit["sha"]
        if sha not in new_shas:
            additions, deletions = get_commit_stats(owner, repo_name, sha, headers)
            new_commit_dicts.append(
                {
                    "repo": repo_name,
                    "author": commit["author"],
                    "author_avatar_url": repo["owner"]["avatar_url"],
                    "message": commit["message"],
                    "date": commit["date"],
                    "url": commit["url"],
                    "additions": additions,
                    "deletions": deletions,
                }
            )
            new_shas.add(sha)

    for release in get_releases(owner, repo_name, headers):
        if release["prerelease"]:
            continue
        release_key = f"{repo_id}/{release['tag']}"
        if release_key not in seen_releases:
            new_release_dicts.append({"repo": repo_name, **release})
            new_seen_releases.add(release_key)


def check_commits(github_token, github_username):
    headers = {"Authorization": f"token {github_token}"} if github_token else {}

    seen_shas = load_seen(SEEN_FILE)
    seen_repos = load_seen(SEEN_REPOS_FILE)
    seen_releases = load_seen(SEEN_RELEASES_FILE)

    new_shas = set(seen_shas)
    new_seen_repos = set(seen_repos)
    new_seen_releases = set(seen_releases)

    new_commit_dicts = []
    new_release_dicts = []
    new_repo_embeds = []

    process_args = (
        headers, seen_repos, seen_releases,
        new_shas, new_seen_repos, new_seen_releases,
        new_commit_dicts, new_release_dicts, new_repo_embeds,
    )

    for repo in get_repos(github_username, headers):
        _process_repo(repo, github_username, f"{github_username}/{repo['name']}", *process_args)

    for repo in get_org_repos(github_username, headers):
        if repo["name"] == ".github":
            continue
        owner = repo["owner"]["login"]
        _process_repo(repo, owner, f"{owner}/{repo['name']}", *process_args)

    save_seen(SEEN_FILE, new_shas)
    save_seen(SEEN_REPOS_FILE, new_seen_repos)
    save_seen(SEEN_RELEASES_FILE, new_seen_releases)

    new_commit_dicts.sort(key=lambda c: c["date"])
    new_release_dicts.sort(key=lambda r: r["published_at"])

    new_commits = [
        embed.show_new_commit(
            c["repo"], c["author"], c["author_avatar_url"],
            c["message"], c["date"], c["url"],
            c.get("additions"), c.get("deletions"),
        )
        for c in new_commit_dicts
    ]

    new_releases = [
        embed.show_new_release(
            r["repo"], r["author"], r["author_avatar_url"],
            r["tag"], r["name"], r["body"], r["url"],
            r["published_at"], r["prerelease"],
        )
        for r in new_release_dicts
    ]

    return new_commits + new_releases + new_repo_embeds

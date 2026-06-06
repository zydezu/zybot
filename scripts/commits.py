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
            "sha": commit.get("sha"),
            "author": commit.get("commit", {}).get("author", {}).get("name"),
            "message": commit.get("commit", {}).get("message"),
            "url": commit.get("html_url"),
            "date": commit.get("commit", {}).get("author", {}).get("date"),
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
            "tag": r.get("tag_name"),
            "name": r.get("name") or r.get("tag_name"),
            "body": r.get("body") or "",
            "url": r.get("html_url"),
            "author": r.get("author", {}).get("login"),
            "author_avatar_url": r.get("author", {}).get("avatar_url"),
            "published_at": r.get("published_at"),
            "prerelease": r.get("prerelease", False),
            "assets_count": len(r.get("assets", [])),
            "zipball_url": r.get("zipball_url"),
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
        org_repos.extend(requests.get(org.get("repos_url"), headers=headers).json())
    return org_repos


def _process_repo(
    repo,
    owner,
    repo_id,
    headers,
    seen_repos,
    seen_releases,
    new_shas,
    new_seen_repos,
    new_seen_releases,
    new_commit_dicts,
    new_release_dicts,
    new_repo_embeds,
):
    repo_name = repo.get("name")
    commits = get_commits(owner, repo_name, headers)

    # hacky way to stop the creation of forks flooding chat
    if repo_id not in seen_repos:
        for commit in commits:
            new_shas.add(commit.get("sha"))
        for release in get_releases(owner, repo_name, headers):
            if not release.get("prerelease"):
                new_seen_releases.add(f"{repo_id}/{release.get('tag')}")
        new_seen_repos.add(repo_id)
        new_repo_embeds.append(
            embed.show_new_repo(
                repo_name,
                repo.get("owner", {}).get("login"),
                repo.get("owner", {}).get("avatar_url"),
                repo.get("html_url"),
                repo.get("fork"),
                repo.get("description"),
            )
        )
        return

    for commit in commits:
        sha = commit.get("sha")
        if sha not in new_shas:
            additions, deletions = get_commit_stats(owner, repo_name, sha, headers)
            new_commit_dicts.append(
                {
                    "repo": repo_name,
                    "author": commit.get("author"),
                    "author_avatar_url": repo.get("owner", {}).get("avatar_url"),
                    "message": commit.get("message"),
                    "date": commit.get("date"),
                    "url": commit.get("url"),
                    "additions": additions,
                    "deletions": deletions,
                }
            )
            new_shas.add(sha)

    for release in get_releases(owner, repo_name, headers):
        if release.get("prerelease"):
            continue
        release_key = f"{repo_id}/{release.get('tag')}"
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
        headers,
        seen_repos,
        seen_releases,
        new_shas,
        new_seen_repos,
        new_seen_releases,
        new_commit_dicts,
        new_release_dicts,
        new_repo_embeds,
    )

    for repo in get_repos(github_username, headers):
        _process_repo(
            repo,
            github_username,
            f"{github_username}/{repo.get('name')}",
            *process_args,
        )

    for repo in get_org_repos(github_username, headers):
        if repo.get("name") == ".github":
            continue
        owner = repo.get("owner", {}).get("login")
        _process_repo(repo, owner, f"{owner}/{repo.get('name')}", *process_args)

    save_seen(SEEN_FILE, new_shas)
    save_seen(SEEN_REPOS_FILE, new_seen_repos)
    save_seen(SEEN_RELEASES_FILE, new_seen_releases)

    new_commit_dicts.sort(key=lambda c: c.get("date"))
    new_release_dicts.sort(key=lambda r: r.get("published_at"))

    new_commits = [
        embed.show_new_commit(
            c.get("repo"),
            c.get("author"),
            c.get("author_avatar_url"),
            c.get("message"),
            c.get("date"),
            c.get("url"),
            c.get("additions"),
            c.get("deletions"),
        )
        for c in new_commit_dicts
    ]

    new_releases = [
        embed.show_new_release(
            r.get("repo"),
            r.get("author"),
            r.get("author_avatar_url"),
            r.get("tag"),
            r.get("name"),
            r.get("body"),
            r.get("url"),
            r.get("published_at"),
            r.get("prerelease"),
            assets_count=r.get("assets_count"),
            zipball_url=r.get("zipball_url"),
        )
        for r in new_release_dicts
    ]

    return new_commits + new_releases + new_repo_embeds

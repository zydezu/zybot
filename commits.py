import embed
import requests, os
from dotenv import load_dotenv

SEEN_FILE = "seencommits.txt"

def get_repos(github_username, headers):
    url = f"https://api.github.com/users/{github_username}/repos"
    return requests.get(url, headers=headers).json()

def get_commits(github_username, repo_name, headers):
    url = f"https://api.github.com/repos/{github_username}/{repo_name}/commits"
    response = requests.get(url, headers=headers)
    commits = response.json()
    result = []
    if isinstance(commits, list):
        for commit in commits:
            result.append({
                "repo": repo_name,
                "sha": commit["sha"],
                "author": commit["commit"]["author"]["name"],
                "message": commit["commit"]["message"],
                "url": commit["html_url"],
                "date": commit["commit"]["author"]["date"]
            })
    return result

def load_seen_shas():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_seen_shas(shas):
    with open(SEEN_FILE, "w") as f:
        for sha in shas:
            f.write(f"{sha}\n")

def check_commits(github_token, github_username):
    headers = {"Authorization": f"token {github_token}"} if github_token else {}

    seen_shas = load_seen_shas()
    new_shas = set(seen_shas)
    repos = get_repos(github_username, headers)

    new_commit_dicts = []

    for repo in repos:
        repo_name = repo["name"]
        commits = get_commits(github_username, repo_name, headers)
        for commit in commits:
            sha = commit["sha"]
            if sha not in seen_shas:
                new_commit_dicts.append({
                    "repo": commit['repo'],
                    "author": commit['author'],
                    "author_avatar_url": repo["owner"]["avatar_url"],
                    "message": commit['message'],
                    "date": commit['date'],
                    "url": commit['url'],
                })
                new_shas.add(sha)

    save_seen_shas(new_shas)

    new_commit_dicts.sort(key=lambda c: c["date"])

    new_commits = [
        embed.show_new_commit(c['repo'], c['author'], c['author_avatar_url'], c['message'], c['date'], c['url'])
        for c in new_commit_dicts
    ]

    return new_commits
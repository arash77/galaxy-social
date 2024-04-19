import os
import requests


def comment_to_github(comment_text, error=False):
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner, repo_name = os.getenv("GITHUB_REPOSITORY").split("/")
    pr_number = os.getenv("PR_NUMBER")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"
    data = {"body": comment_text}
    print(f"Posting comment to {url}")
    response = requests.post(url, headers=headers, json=data)
    print(response.json())
    if response.status_code != 201:
        raise Exception("Failed to create github comment!")
    else:
        if error:
            raise Exception(comment_text)
        return True

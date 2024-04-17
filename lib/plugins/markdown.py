import time
import requests
import os


class markdown_client:
    def __init__(self, **kwargs):
        self.save_path = kwargs.get("save_path")

    def create_post(self, content, mentions, hashtags, images):
        try:
            medias = "\n".join(
                [f'![{image.get("alt_text", "")}]({image["url"]})' for image in images]
            )
            mentions = " ".join([f"@{v}" for v in mentions])
            hashtags = " ".join([f"#{v}" for v in hashtags])
            text = f"{content}\n{mentions}\n{hashtags}\n{medias}"
            if self.save_path:
                with open(
                    f"{self.save_path}/{time.strftime('%Y%m%d-%H%M%S')}.md", "w"
                ) as f:
                    f.write(text)
            print(os.getenv("PREVIEW"))
            if os.getenv("PREVIEW"):
                github_token = os.getenv("GITHUB_TOKEN")
                repo_owner, repo_name = os.getenv("GITHUB_REPOSITORY").split("/")
                pr_number = os.getenv("GITHUB_REF_NAME").split("/")[0]
                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {github_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"
                data = {"body": text}
                response = requests.post(url, headers=headers, json=data)
                if response.status_code != 201:
                    raise Exception("Failed to create comment")
            return True
        except:
            return False

import time
import os
from github_comment import comment_to_github


class markdown_client:
    def __init__(self, **kwargs):
        self.save_path = kwargs.get("save_path")

    def create_post(self, content, mentions, hashtags, images, **kwargs):
        try:
            medias = "\n".join(
                [f'![{image.get("alt_text", "")}]({image["url"]})' for image in images]
            )
            mentions = " ".join([f"@{v}" for v in mentions])
            hashtags = " ".join([f"#{v}" for v in hashtags])
            social_media = ", ".join(kwargs.get("media"))
            text = f"This is a preview that will be posted to {social_media}:\n\n{content}\n{mentions}\n{hashtags}\n{medias}"
            if self.save_path:
                os.makedirs(self.save_path, exist_ok=True)
                with open(
                    f"{self.save_path}/{time.strftime('%Y%m%d-%H%M%S')}.md", "w"
                ) as f:
                    f.write(text)
            if os.getenv("PREVIEW"):
                comment_to_github(text)
            return True, None
        except:
            return False, None

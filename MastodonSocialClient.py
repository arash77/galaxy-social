from mastodon import Mastodon
from bs4 import BeautifulSoup
import textwrap
import requests
from urllib.parse import urlparse

class mastodon_social_client:
    def __init__(self, access_token=None, api_base_url='https://mstdn.science'):
        self.mastodon_handle = Mastodon(access_token = access_token, api_base_url = api_base_url)
        self.max_content_length = 500

    def create_post(self, content, mentions, hashtags, images, alt_texts):
        content = content + '\n' + mentions + '\n' + hashtags
        toot_id = None
        status = []
        if images:
            media_ids = []
            for image in images[:4]:
                response = requests.get(image)
                if response.status_code == 200:
                    parsed_url = urlparse(image)
                    filename = parsed_url.path.split("/")[-1]
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                        media = self.mastodon_handle.media_post(media_file=filename, description=alt_texts[images.index(image)])
                        media_ids.append(media['id'])

        for text in textwrap.wrap(content, self.max_content_length):
            toot = self.mastodon_handle.status_post(status=text, in_reply_to_id=toot_id, media_ids=media_ids if images and toot_id == None else None)
            toot_id = toot.id
            mastodon_post = self.mastodon_handle.status(toot.id)
            post_content = BeautifulSoup(mastodon_post.content, 'html.parser').get_text(separator=' ')
            status.append(''.join(post_content.split()) == ''.join(text.split()))
        
        return all(status)
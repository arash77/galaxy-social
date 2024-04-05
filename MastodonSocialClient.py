from mastodon import Mastodon
from bs4 import BeautifulSoup
import textwrap
import requests

class mastodon_social_client:
    def __init__(self, access_token=None, api_base_url='https://mstdn.science'):
        self.mastodon_handle = Mastodon(access_token = access_token, api_base_url = api_base_url)
        self.max_content_length = 500

    def create_post(self, content, mentions, hashtags, images, alt_texts):
        if images:
            media_ids = []
            for image in images[:4]:
                response = requests.get(image)
                filename = image.split('/')[-1]
                if response.status_code == 200:
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    media = self.mastodon_handle.media_post(media_file=filename, description=alt_texts[images.index(image)])
                    media_ids.append(media['id'])

        toot_id = None
        status = []
        for text in textwrap.wrap(content + '\n' + mentions + '\n' + hashtags, self.max_content_length, replace_whitespace=False):
            toot = self.mastodon_handle.status_post(status=text, in_reply_to_id=toot_id, media_ids=media_ids if (media_ids != [] and toot_id == None) else None)
            toot_id = toot.id
            for _ in range(3):
                post = self.mastodon_handle.status(toot_id)
                if post.content:
                    break
            post_content = BeautifulSoup(post.content, 'html.parser').get_text(separator=' ')
            status.append(''.join(post_content.split()) == ''.join(text.split()))
        
        return all(status)
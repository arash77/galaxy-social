from mastodon import Mastodon
from bs4 import BeautifulSoup

class mastodon_social_client:
    def __init__(self, access_token=None, api_base_url='https://mstdn.science'):
        self.mastodon_handle = Mastodon(access_token = access_token, api_base_url = api_base_url)

    def post(self, content):
        if len(content) > 500:
            content = content[:497] + '...'
        post = self.mastodon_handle.toot(content)
        for _ in range(3):
            try:
                mastodon_post = self.mastodon_handle.status(post.id)
                post_content = BeautifulSoup(mastodon_post.content, 'html.parser').get_text(separator=' ')
                return ''.join(post_content.split()) == ''.join(content.split())
            except:
                return False
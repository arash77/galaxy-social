import os
import markdown
import atproto
import requests
from mastodon import Mastodon
import json
from bs4 import BeautifulSoup
import re
from typing import Dict, List

blueskysocial = atproto.Client(base_url='https://bsky.social')
blueskysocial.login(os.environ.get('BLUESKY_USERNAME'), os.environ.get('BLUESKY_PASSWORD'))

mastodon_handle = Mastodon(access_token = os.environ.get('MASTODON_ACCESS_TOKEN'),api_base_url = 'https://mstdn.science')

class LinkedIn():
    def __init__(self):
        self.access_token = os.environ.get('LINKEDIN_ACCESS_TOKEN')
        self.api_base_url = 'https://api.linkedin.com/rest/'
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202403',
        }

    def post(self, content):
        url = self.api_base_url + 'posts'
        data = {
                "author": "urn:li:organization:5515715",
                "commentary": content,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": []
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False
                }
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()
    
    def get_profile(self):
        url = self.api_base_url + 'people/~'
        response = requests.get(url, headers=self.headers)
        return response.json()

linkedin_handle = LinkedIn()



class MetadataHeader:
    def __init__(self, social_media=[]):
        self.social_media = social_media
        
def parse_markdown_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        metadata = MetadataHeader()
        for line in content.split('\n'):
            if line.startswith('social_media:'):
                metadata.social_media = line.split(':')[1].strip().replace(' ', '').split(',')
        text = content.split('---')[2].lstrip('\n')
        markdown_content = markdown.markdown(text)
        plain_content = BeautifulSoup(markdown_content, 'html.parser').get_text(separator='\n')
        return plain_content, metadata


def parse_mentions(text: str) -> List[Dict]:
    spans = []
    mention_regex = rb"[$|\W](@([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(mention_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "handle": m.group(1)[1:].decode("UTF-8")
        })
    return spans

def parse_urls(text: str) -> List[Dict]:
    spans = []
    url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(url_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "url": m.group(1).decode("UTF-8"),
        })
    return spans

def parse_hashtags(text: str) -> List[Dict]:
    spans = []
    hashtag_regex = rb"[$|\W]#(\w+)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(hashtag_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "tag": m.group(1).decode("UTF-8"),
        })
    return spans

def parse_facets(text: str) -> List[Dict]:
    facets = []
    for h in parse_hashtags(text):
        facets.append({
            "index": {
                "byteStart": h["start"],
                "byteEnd": h["end"],
            },
            "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": h["tag"]}],
        })
    for m in parse_mentions(text):
        resp = requests.get(
            "https://bsky.social/xrpc/com.atproto.identity.resolveHandle",
            params={"handle": m["handle"]},
        )
        if resp.status_code == 400:
            continue
        did = resp.json()["did"]
        facets.append({
            "index": {
                "byteStart": m["start"],
                "byteEnd": m["end"],
            },
            "features": [{"$type": "app.bsky.richtext.facet#mention", "did": did}],
        })
    embed_external = None
    for u in parse_urls(text):
        facets.append({
            "index": {
                "byteStart": u["start"],
                "byteEnd": u["end"],
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": u["url"],
                }
            ],
        })
        response = requests.get(u["url"])
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            embed_external = atproto.models.AppBskyEmbedExternal.Main(
                external=atproto.models.AppBskyEmbedExternal.External(
                    title=soup.find('meta', attrs={'property': 'og:title'})['content'] if soup.find('meta', attrs={'property': 'og:title'}) else soup.title.string,
                    description=soup.find('meta', attrs={'property': 'og:description'})['content'] if soup.find('meta', attrs={'property': 'og:description'}) else soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else soup.title.string,
                    uri=u["url"],
                    thumb=blueskysocial.upload_blob(requests.get(soup.find('meta', attrs={'property': 'og:image'})['content']).content).blob if soup.find('meta', attrs={'property': 'og:image'}) else None,
                )
            )
    return facets, embed_external

def post_to_bluesky(content):
    if len(content) > 300:
        content = content[:297] + '...'
    facets, embed_external = parse_facets(content)
    post = blueskysocial.send_post(content, facets=facets, embed=embed_external)
    for _ in range(3):
        try:
            data = blueskysocial.get_author_feed(
                actor=post.uri[post.uri.find('did:plc:'):post.uri.find('/app.bsky.feed.post')], 
                filter='posts_and_author_threads',
                limit=1,
            )
            post_text = data.feed[0].post.record.text
            return post_text == content
        except:
            return False
        
def post_to_mastodon(content):
    if len(content) > 500:
        content = content[:497] + '...'
    post = mastodon_handle.toot(content)
    for _ in range(3):
        try:
            mastodon_post = mastodon_handle.status(post.id)
            post_content = BeautifulSoup(mastodon_post.content, 'html.parser').get_text(separator=' ')
            return ''.join(post_content.split()) == ''.join(content.split())
        except:
            return False

def post_to_linkedin(content):
    linkedin_handle.post(content)
    linkedin_posts = linkedin_handle.get_profile()
    for post in linkedin_posts['activity']:
        if content in post['body']['text']:
            return True
    return False


def process_markdown_files():
    current_folder = os.path.dirname(os.path.abspath(__file__))
    toots_folder = os.path.join(current_folder, 'toots')
    processed_files = {}
    if os.path.exists('processed_files.json'):
        with open('processed_files.json', 'r') as file:
            processed_files = json.load(file)
    for file_name in os.listdir(toots_folder):
        if file_name.endswith('.toot') and not processed_files.get(file_name):
            file_path = os.path.join(toots_folder, file_name)
            content, metadata = parse_markdown_file(file_path)
            stats = {}
            for channel in metadata.social_media:
                if channel == 'bluesky':
                    stats[channel] = post_to_bluesky(content)
                elif channel == 'linkedin':
                    stats[channel] = post_to_linkedin(content)
                elif channel == 'mastodon':
                    stats[channel] = post_to_mastodon(content)
            processed_files[file_name] = stats
            print(f'Processed {file_name}: {stats}')
    with open('processed_files.json', 'w') as file:
        json.dump(processed_files, file)
        
if __name__ == '__main__':
    process_markdown_files()

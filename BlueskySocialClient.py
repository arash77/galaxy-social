import re
from typing import Dict, List
import atproto

import requests
from bs4 import BeautifulSoup

class bluesky_social_client:
    def __init__(self, base_url='https://bsky.social', username=None, password=None):
        self.blueskysocial = atproto.Client(base_url=base_url)
        self.blueskysocial.login(username=username, password=password)

    def parse_mentions(self, text: str) -> List[Dict]:
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

    def parse_urls(self, text: str) -> List[Dict]:
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

    def parse_hashtags(self, text: str) -> List[Dict]:
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

    def parse_facets(self, text: str) -> List[Dict]:
        facets = []
        for h in self.parse_hashtags(text):
            facets.append({
                "index": {
                    "byteStart": h["start"],
                    "byteEnd": h["end"],
                },
                "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": h["tag"]}],
            })
        for m in self.parse_mentions(text):
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
        for u in self.parse_urls(text):
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
                        thumb=self.blueskysocial.upload_blob(requests.get(soup.find('meta', attrs={'property': 'og:image'})['content']).content).blob if soup.find('meta', attrs={'property': 'og:image'}) else None,
                    )
                )
        return facets, embed_external

    def post(self, content):
        if len(content) > 300:
            content = content[:297] + '...'
        facets, embed_external = self.parse_facets(content)
        post = self.blueskysocial.send_post(content, facets=facets, embed=embed_external)
        for _ in range(3):
            try:
                data = self.blueskysocial.get_author_feed(
                    actor=post.uri[post.uri.find('did:plc:'):post.uri.find('/app.bsky.feed.post')], 
                    filter='posts_and_author_threads',
                    limit=1,
                )
                post_text = data.feed[0].post.record.text
                return post_text == content
            except:
                return False
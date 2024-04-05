import re
from typing import Dict, List
import atproto
import requests
from bs4 import BeautifulSoup
import textwrap

class bluesky_social_client:
    def __init__(self, base_url='https://bsky.social', username=None, password=None):
        self.base_url = base_url
        self.blueskysocial = atproto.Client(base_url=base_url)
        self.blueskysocial.login(login=username, password=password)
        self.max_content_length = 300

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
        last_url = None
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
            last_url = u["url"]
        return facets, last_url
    
    def handle_url_card(self, url: str):
        try:
            response = requests.get(url)
        except:
            return None
        embed_external = None
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('meta', attrs={'property': 'og:title'})
            title_tag_alt = soup.title.string
            description_tag = soup.find('meta', attrs={'property': 'og:description'})
            description_tag_alt = soup.find('meta', attrs={'name': 'description'})
            image_tag = soup.find('meta', attrs={'property': 'og:image'})
            title = title_tag['content'] if title_tag else title_tag_alt
            description = description_tag['content'] if description_tag else description_tag_alt['content'] if description_tag_alt else None
            uri=url
            thumb=self.blueskysocial.upload_blob(requests.get(image_tag['content']).content).blob if image_tag else None
            embed_external = atproto.models.AppBskyEmbedExternal.Main(
                external=atproto.models.AppBskyEmbedExternal.External(
                    title=title,
                    description=description,
                    uri=uri,
                    thumb=thumb,
                )
            )
        return embed_external

    def parse_uri(uri: str) -> Dict:
        if uri.startswith("at://"):
            repo, collection, rkey = uri.split("/")[2:5]
            return {"repo": repo, "collection": collection, "rkey": rkey}
        elif uri.startswith("https://bsky.app/"):
            repo, collection, rkey = uri.split("/")[4:7]
            if collection == "post":
                collection = "app.bsky.feed.post"
            elif collection == "lists":
                collection = "app.bsky.graph.list"
            elif collection == "feed":
                collection = "app.bsky.feed.generator"
            return {"repo": repo, "collection": collection, "rkey": rkey}
        else:
            raise Exception("unhandled URI format: " + uri)


    def create_post(self, content, mentions, hashtags, images, alt_texts):
        if images:
            embed_images = []
            for image in images[:4]:
                response = requests.get(image)
                if response.status_code == 200:
                    img_data = response.content
                    upload = self.blueskysocial.com.atproto.repo.upload_blob(img_data)
                    embed_images.append(atproto.models.AppBskyEmbedImages.Image(alt=alt_texts[images.index(image)], image=upload.blob))
            embed=atproto.models.AppBskyEmbedImages.Main(images=embed_images)

        status = []
        reply_to = None
        for text in textwrap.wrap(content + '\n' + mentions + '\n' + hashtags, self.max_content_length, replace_whitespace=False):
            facets, last_url = self.parse_facets(text)
            if not images or reply_to is not None:
                embed = self.handle_url_card(last_url)

            post = self.blueskysocial.send_post(text, facets=facets, embed=embed, reply_to=reply_to)
            if reply_to is None:
                root = atproto.models.create_strong_ref(post)
            parent = atproto.models.create_strong_ref(post)
            reply_to = atproto.models.AppBskyFeedPost.ReplyRef(parent=parent, root=root)

            post_id = self.parse_uri(post['uri'])['repo']
            data = self.blueskysocial.get_author_feed(actor=post_id, filter='posts_and_author_threads', limit=1)
            post_text = data.feed[0].post.record.text
            status.append(post_text == text)
        
        return all(status)
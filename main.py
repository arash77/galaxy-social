import os
import markdown
import json
from bs4 import BeautifulSoup
from BlueskySocialClient import bluesky_social_client
from MastodonSocialClient import mastodon_social_client
from LinkedinSocialClient import linkedin_social_client
import re


bluesky_handle = bluesky_social_client(username=os.environ.get('BLUESKY_USERNAME'), password=os.environ.get('BLUESKY_PASSWORD'))
mastodon_handle = mastodon_social_client(access_token=os.environ.get('MASTODON_ACCESS_TOKEN'))
linkedin_handle = linkedin_social_client(access_token=os.environ.get('LINKEDIN_ACCESS_TOKEN'))



class MetadataHeader:
    def __init__(self, social_media=[], mentions=[], hashtags=[], images=[], alt_texts=[]):
        self.social_media = social_media
        self.mentions = mentions
        self.hashtags = hashtags
        self.images = images
        self.alt_texts = alt_texts
        
def parse_markdown_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        metadata = MetadataHeader()
        for line in content.split('\n'):
            if line.startswith('social_media:'):
                metadata.social_media = line.split(':')[1].strip().replace(' ', '').lower().split(',')
            if line.startswith('mentions:'):
                metadata.mentions = line.split(':')[1].strip().replace(' ', '')
            if line.startswith('hashtags:'):
                metadata.hashtags = line.split(':')[1].strip().replace(' ', '')
            if line.startswith('images:'):
                metadata.images = line.split(':')[1].strip().replace(' ', '').split(',')
            if line.startswith('alt_texts:'):
                metadata.alt_texts = line.split(':')[1].strip().replace(' ', '').split(',')
            
        text = content.split('---')[2].lstrip('\n')
        markdown_content = markdown.markdown(text)
        plain_content = BeautifulSoup(markdown_content, 'html.parser').get_text(separator='\n')
        return plain_content, metadata

def fetch_mention_hashtag(metadata, social_media):
    mentions, hashtags = '', ''
    for type, text in {'mention': metadata.mentions, 'hashtag': metadata.hashtags}.items():
        match = re.search(rf'{social_media}\[(.*?)\]', text)
        if match:
            values = match.group(1).split(',')
            if type == 'mention':
                mentions = ' '.join([f"@{v}" for v in values])
            elif type == 'hashtag':
                hashtags = ' '.join([f"#{v}" for v in values])
    return mentions, hashtags
    


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
                mentions, hashtags = fetch_mention_hashtag(metadata, channel)
                if channel == 'bluesky':
                    stats[channel] = bluesky_handle.create_post(content, mentions, hashtags, metadata.images, metadata.alt_texts)
                elif channel == 'mastodon':
                    stats[channel] = mastodon_handle.create_post(content, mentions, hashtags, metadata.images, metadata.alt_texts)
                elif channel == 'linkedin':
                    stats[channel] = False
                    # stats[channel] = linkedin_handle.create_post(content, mentions, hashtags, metadata.images, metadata.alt_texts)
            processed_files[file_name] = stats
            print(f'Processed {file_name}: {stats}')
    with open('processed_files.json', 'w') as file:
        json.dump(processed_files, file)
        
if __name__ == '__main__':
    process_markdown_files()

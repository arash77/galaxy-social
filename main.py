import os
import markdown
import json
from bs4 import BeautifulSoup
import re
import yaml
import importlib

with open('plugins.yml', 'r') as file:
    plugins_config = yaml.safe_load(file)

plugins = {}
for plugin in plugins_config['plugins']:
    if plugin['enabled']:
        module_name, class_name = plugin['class'].rsplit('.', 1)
        module = importlib.import_module('plugins.'+module_name)
        plugin_class = getattr(module, class_name)
        config = {key: os.environ.get(value) for key, value in plugin['config'].items()}
        plugins[plugin['name'].lower()] = plugin_class(**config)


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
                metadata.social_media = line.split('social_media:', 1)[1].strip().replace(' ', '').lower().split(',')
            if line.startswith('mentions:'):
                metadata.mentions = line.split('mentions:', 1)[1].strip().replace(' ', '')
            if line.startswith('hashtags:'):
                metadata.hashtags = line.split('hashtags:', 1)[1].strip().replace(' ', '')
            if line.startswith('images:'):
                metadata.images = line.split("images:", 1)[1].strip().split('"')[1::2]
            if line.startswith('alt_texts:'):
                metadata.alt_texts = line.split("alt_texts:", 1)[1].strip().split('"')[1::2]
            
        text = content.split('---')[2].lstrip('\n')
        markdown_content = markdown.markdown(text)
        plain_content = BeautifulSoup(markdown_content, 'html.parser').get_text(separator='\n')
        return plain_content, metadata

def fetch_mention_hashtag(metadata, social_media):
    mentions, hashtags = [], []
    for type, text in {'mention': metadata.mentions, 'hashtag': metadata.hashtags}.items():
        if not text:
            continue
        match = re.search(rf'{social_media}\[(.*?)\]', text)
        if match:
            values = match.group(1).split(',')
            if type == 'mention':
                mentions = values
            elif type == 'hashtag':
                hashtags = values
    return mentions, hashtags
    


def process_markdown_files():
    current_folder = os.path.dirname(os.path.abspath(__file__))
    posts_folder = os.path.join(current_folder, 'posts')
    processed_files = {}
    if os.path.exists('processed_files.json'):
        with open('processed_files.json', 'r') as file:
            processed_files = json.load(file)
    for file_name in os.listdir(posts_folder):
        if file_name.endswith('.md') and not processed_files.get(file_name):
            file_path = os.path.join(posts_folder, file_name)
            content, metadata = parse_markdown_file(file_path)
            stats = {}
            for channel in metadata.social_media:
                mentions, hashtags = fetch_mention_hashtag(metadata, channel)
                stats[channel] = plugins[channel].create_post(content, mentions, hashtags, metadata.images, metadata.alt_texts)
            processed_files[file_name] = stats
            print(f'Processed {file_name}: {stats}')
    with open('processed_files.json', 'w') as file:
        json.dump(processed_files, file)
        
if __name__ == '__main__':
    process_markdown_files()

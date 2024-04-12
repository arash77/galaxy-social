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
        config = {key: os.environ.get(value) for key, value in plugin['config'].items() if os.environ.get(value) is not None}
        plugins[plugin['name'].lower()] = plugin_class(**config)


        
def parse_markdown_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    metadata = yaml.safe_load(content.split('---')[1])
    metadata['social_media'] = [social_media.lower() for social_media in metadata['social_media']]
    metadata['mentions'] = {key.lower(): value for key, value in metadata['mentions'].items()} if metadata.get('mentions') else {}
    metadata['hashtags'] = {key.lower(): value for key, value in metadata['hashtags'].items()} if metadata.get('hashtags') else {}
    text = content.split('---')[2].lstrip('\n')
    markdown_content = markdown.markdown(text)
    plain_content = BeautifulSoup(markdown_content, 'html.parser').get_text(separator='\n')
    return plain_content, metadata
    


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
            for social_media in metadata['social_media']:
                mentions = metadata.get('mentions', {}).get(social_media, [])
                hashtags = metadata.get('hashtags', {}).get(social_media, [])
                images = metadata.get('images', [])
                stats[social_media] = plugins[social_media].create_post(content, mentions, hashtags, images)
            processed_files[file_name] = stats
            print(f'Processed {file_name}: {stats}')
    with open('processed_files.json', 'w') as file:
        json.dump(processed_files, file)
        
if __name__ == '__main__':
    process_markdown_files()

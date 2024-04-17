import os
import markdown
import json
from bs4 import BeautifulSoup
import fnmatch
import yaml
import importlib
import jsonschema

with open("plugins.yml", "r") as file:
    plugins_config = yaml.safe_load(file)

plugins = {}
for plugin in plugins_config["plugins"]:
    if os.getenv("PREVIEW") and plugin["name"] != "markdown":
        continue

    if plugin["enabled"]:
        module_name, class_name = plugin["class"].rsplit(".", 1)

        try:
            module = importlib.import_module(f"plugins.{module_name}")
            plugin_class = getattr(module, class_name)
        except ModuleNotFoundError:
            raise RuntimeError(f"Plugin {module_name}.{class_name} not found")

        try:
            config = {
                key: os.environ.get(value)
                for key, value in plugin["config"].items()
                if (not isinstance(value, int) and os.environ.get(value) is not None)
            }
        except KeyError:
            raise RuntimeError(f"Missing config for {module_name}.{class_name}")

        try:
            plugins[plugin["name"].lower()] = plugin_class(**config)
        except TypeError:
            raise RuntimeError(f"Invalid config for {module_name}.{class_name}.")


def parse_markdown_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    _, metadata, text = content.split("---\n", 2)
    try:
        metadata = yaml.safe_load(metadata)
        with open(".schema.yaml", "r") as f:
            schema = yaml.safe_load(f)
        jsonschema.validate(instance=metadata, schema=schema)
    except:
        raise Exception(f"Invalid metadata in {file_path}")

    metadata["media"] = [media.lower() for media in metadata["media"]]
    metadata["mentions"] = (
        {key.lower(): value for key, value in metadata["mentions"].items()}
        if metadata.get("mentions")
        else {}
    )
    metadata["hashtags"] = (
        {key.lower(): value for key, value in metadata["hashtags"].items()}
        if metadata.get("hashtags")
        else {}
    )
    markdown_content = markdown.markdown(text.strip())
    plain_content = BeautifulSoup(markdown_content, "html.parser").get_text(
        separator="\n"
    )
    return plain_content, metadata


def process_markdown_file(file_path, processed_files):
    content, metadata = parse_markdown_file(file_path)
    stats = {}
    for media in metadata["media"]:
        if file_path in processed_files and media in processed_files[file_path]:
            stats[media] = processed_files[file_path][media]
            continue
        mentions = metadata.get("mentions", {}).get(media, [])
        hashtags = metadata.get("hashtags", {}).get(media, [])
        images = metadata.get("images", [])
        print(f"Processing {os.getenv('PREVIEW')} for {media}")
        if not os.getenv("PREVIEW") or media == "markdown":
            print(f"Creating post for {media}")
            stats[media] = plugins[media].create_post(
                content, mentions, hashtags, images
            )
    processed_files[file_path] = stats
    print(f"Processed {file_path}: {stats}")
    return processed_files


def main():
    processed_files = {}
    if os.path.exists("processed_files.json"):
        with open("processed_files.json", "r") as file:
            processed_files = json.load(file)
    changed_files = os.environ.get("CHANGED_FILES")
    if changed_files:
        for file_path in json.loads(changed_files):
            print(f"Processing {file_path}")
            if file_path.endswith(".md"):
                processed_files = process_markdown_file(file_path, processed_files)
    else:
        for root, _, files in os.walk("posts"):
            for filename in fnmatch.filter(files, "*.md"):
                file_path = os.path.join(root, filename)
                processed_files = process_markdown_file(file_path, processed_files)
    with open("processed_files.json", "w") as file:
        json.dump(processed_files, file)


if __name__ == "__main__":
    main()

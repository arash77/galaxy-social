from slack_sdk import WebClient
import requests
import os

class slack_social_client:
    def __init__(self, access_token=None, channel_id=None):
        self.client = WebClient(token=access_token)
        self.channel_id = channel_id

    def upload_images(self, images, alt_texts, text):
        uploaded_files = []
        if len(images) > len(alt_texts):
            alt_texts += [''] * (len(images) - len(alt_texts))
        for image_url, alt_text in zip(images, alt_texts):
            filename = image_url.split('/')[-1]

            with requests.get(image_url) as response:
                if response.status_code != 200:
                    continue
                content_length = len(response.content)
                with open(filename, 'wb') as temp_file:
                    temp_file.write(response.content)

            response = self.client.files_getUploadURLExternal(filename=filename, length=content_length, alt_txt=alt_text)
            upload_url = response.data['upload_url']
            with open(filename, 'rb') as temp_file:
                with requests.post(upload_url, files={'file': temp_file}) as upload_response:
                    if upload_response.status_code != 200:
                        continue
            uploaded_files.append({'id': response.data['file_id']})
            os.remove(filename)

        response = self.client.files_completeUploadExternal(files=uploaded_files, channel_id=self.channel_id, initial_comment=text)
        return response['ok']

    def create_post(self, text, mentions, hashtags, images, alt_texts):
        if images:
            response = self.upload_images(images, alt_texts, text)
        else:
            response = self.client.chat_postMessage(channel=self.channel_id, text=text)['ok']
        return response
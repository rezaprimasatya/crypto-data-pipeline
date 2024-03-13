import requests
import mimetypes
import json
import io

from typing import Optional, Dict, Any, List, Union


class DiscordClient(object):
    BASE_URL = 'https://discord.com/api/v9'
    TIMEOUT = 10

    def __init__(self, token: str, url: str=None):
        self._token = token
        if url != None:
            self.BASE_URL = url
        self._session = self._get_session()

    def _request(self, method: str, params={}, uri: str='', headers: dict={}, files:dict=None) -> dict:
        uri_path = uri
        data_json = ''
        if method in ['GET', 'DELETE']:
            if params:
                strl = []
                for key in sorted(params):
                    strl.append('{}={}'.format(key, params[key]))
                data_json += '&'.join(strl)
                uri += f'?{data_json}'
        else:
            if params:
                data_json = params 
        try:
            payload: dict = json.dumps(data_json)
        except:
            payload: dict = data_json

        url = f'{self.BASE_URL}{uri}'
        response = None

        if method == 'GET':
            response = self._session.get(url=url, headers=headers, timeout=self.TIMEOUT)
        elif method == 'DELETE':
            response = self._session.delete(url=url, headers=headers, timeout=self.TIMEOUT)
        elif method == 'POST':
            response = self._session.post(url=url, data=payload, headers=headers, files=files, timeout=self.TIMEOUT)
        elif method == 'PATCH':
            response = self._session.patch(url=url, data=payload, headers=headers, timeout=self.TIMEOUT)
        elif method == 'PUT':
            response = self._session.put(url=url, data=payload, headers=headers, timeout=self.TIMEOUT)
        if response != None:
            return self.check_response(response)

    def _get_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            'authorization': f'Bot {self._token}',
            'content-type': 'application/json',
            'user-agent': 'python-discord-client'
        })

        return session

    def _send_file_attachment(self, method: str, uri: str, files_names: List[str], payload: dict={}, headers: dict={}) -> dict:
        self._session.headers.update({ 'content-type': None })
        headers = { 'content-disposition': 'form-data; name="payload_json"' }
        payload: dict = { 'payload_json': json.dumps(payload) }
        prepared_files: dict = {}
        for i, filename in enumerate(files_names):
            mimetype = (
                mimetypes.guess_type(filename) or "application/octet-stream"
            )

            prepared_files[f'files[{i}]'] = (filename, open(filename, 'rb'), mimetype, {
                'Content-Disposition': f'form-data; name="files[{i}]"; filename="{filename}"'
                }
            )

        for key in prepared_files:
            payload[key] = prepared_files[key]

        response = self._request(method, params=payload, files=prepared_files, headers=headers, uri=uri)
        self._session.headers.update({ 'content-type': 'application/json' })
        return response


    def _send_bytes_attachment(self, method: str, uri: str, files_bytes: List[Dict[str, io.BytesIO]], payload: dict={}, headers: dict={}) -> dict:
        self._session.headers.update({ 'content-type': None })
        headers = { 'content-disposition': 'form-data; name="payload_json"' }
        payload: dict = { 'payload_json': json.dumps(payload) }
        prepared_files: dict = {}
        for i, object in enumerate(files_bytes):
            file_name = object['file_name']
            mimetype = (
                mimetypes.guess_type(file_name) or "application/octet-stream"
            )

            data = object['data']
            data.seek(0)

            prepared_files[f'files[{i}]'] = (file_name, data.read(), mimetype, {
                'Content-Disposition': f'form-data; name="files[{i}]"; filename="{file_name}"'
                }
            )

        for key in prepared_files:
            payload[key] = prepared_files[key]

        response = self._request(method, params=payload, files=prepared_files, headers=headers, uri=uri)
        self._session.headers.update({ 'content-type': 'application/json' })
        return response


    @staticmethod
    def check_response(response) -> dict:
        if f'{response.status_code}'[0] == '2':
            try:
                data = response.json()
            except ValueError:
                raise Exception(response.content)
            else:
                return data
        else:
            raise Exception(f'{response.status_code}: {response.text}')

    def create_message(self,
        channel_id,
        content: str=None,
        tts: bool=None,
        embeds: List[dict]=None,
        allowed_mentions=None,
        message_reference=None,
        components: list=None,
        files: Union[List[str], List[bytes]]=None,
        attachments: List[dict]=None,
        sticker_ids: list=None,
        flags: int=None,
    ) -> dict:
        '''https://discord.com/developers/docs/resources/channel#create-message'''

        payload: dict = {
            'content': content,
            'tts': tts,
            'allowed_mentions': allowed_mentions,
            'message_reference': message_reference,
            'components': components,
            'sticker_ids': sticker_ids,
            'flags': flags,
            'embeds': embeds,
            'attachments': attachments
        }
        payload: dict = {k:v for k,v in payload.items() if v is not None}
        uri = f'/channels/{channel_id}/messages'
        if files != None:
            if isinstance(files[0], str):
                return  self._send_file_attachment(method='POST', uri=uri, files_names=files, payload=payload)
            elif isinstance(files[0], dict):
                return  self._send_bytes_attachment(method='POST', uri=uri, files_bytes=files, payload=payload)
        else:
            return  self._request(method='POST', uri=uri, params=payload)

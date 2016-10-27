# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import base64
from contextlib import closing

import requests
import hashlib


class BackBlazeB2(object):
    def __init__(self, app_key=None, account_id=None, bucket_name=None, bucket_id=None):
        self.bucket_id = None
        self.account_id = account_id
        self.app_key = app_key
        self.bucket_name = bucket_name
        self.bucket_id = bucket_id
        self.authorize()

    def authorize(self):
        headers = {'Authorization': 'Basic: %s' % (base64.b64encode(('%s:%s' % (self.account_id, self.app_key)).encode('utf-8'))).decode('utf-8')}
        response = requests.get('https://api.backblaze.com/b2api/v1/b2_authorize_account', headers=headers)
        if response.status_code == 200:
            resp = response.json()
            self.base_url = resp['apiUrl']
            self.download_url = resp['downloadUrl']
            self.authorization_token = resp['authorizationToken']

            return True

        else:
            return False

    def get_upload_url(self):
        url = self._build_url('/b2api/v1/b2_get_upload_url')
        headers = {'Authorization': self.authorization_token}
        params = {'bucketId': self.bucket_id}
        return requests.get(url, headers=headers, params=params).json()

    def _build_url(self, endpoint=None, authorization=True):
        return "%s%s" % (self.base_url, endpoint)

    def upload_file(self, name, content):
        response = self.get_upload_url()
        if 'uploadUrl' not in response:
            return False

        url = response['uploadUrl']
        sha1_of_file_data = hashlib.sha1(content.read()).hexdigest()
        content.seek(0)

        headers = {
            'Authorization': response['authorizationToken'],
            'X-Bz-File-Name': name,
            'Content-Type': "b2/x-auto",
            'X-Bz-Content-Sha1': sha1_of_file_data,
            'X-Bz-Info-src_last_modified_millis': '',
        }

        download_response = requests.post(url, headers=headers, data=content.read())
        if download_response.status_code != 200:
            # raise exception here.
            pass
        else:
            pass

        return download_response.json()

    def get_file_info(self, name):
        headers = {'Authorization': self.authorization_token}
        return requests.get("%s/file/%s/%s" % (self.download_url, self.bucket_name, name), headers=headers)

    def download_file(self, name):
        headers = {'Authorization': self.authorization_token}
        return requests.get("%s/file/%s/%s" % (self.download_url, self.bucket_name, name), headers=headers).content

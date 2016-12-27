# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import base64
import datetime
import hashlib
import requests
import logging

log = logging.getLogger(__name__)


class BackBlazeB2(object):
    class APIError(Exception):
        pass

    def __init__(self, app_key=None, account_id=None, bucket_name=None, bucket_id=None, bucket_private=True):
        self.bucket_id = None
        self.account_id = account_id
        self.app_key = app_key
        self.bucket_name = bucket_name
        self.bucket_id = bucket_id
        self.bucket_private = bucket_private

        self._authorization_token = None
        self.last_authorized = None
        self.download_url = None
        self.base_url = None

    @property
    def authorization_token(self):
        self.authorize()
        return self._authorization_token

    def authorize(self):
        # Refresh token every 12h
        if self.last_authorized and datetime.datetime.now() < (self.last_authorized + datetime.timedelta(hours=12)):
            return True

        headers = {'Authorization': 'Basic: %s' % (
        base64.b64encode(('%s:%s' % (self.account_id, self.app_key)).encode('utf-8'))).decode('utf-8')}

        response = requests.get('https://api.backblaze.com/b2api/v1/b2_authorize_account', headers=headers, timeout=2)
        if response.status_code == 200:
            resp = response.json()
            self.base_url = resp['apiUrl']
            self.download_url = resp['downloadUrl']
            self._authorization_token = resp['authorizationToken']
            self.last_authorized = datetime.datetime.now()

            return True
        else:
            return False

    def get_upload_url(self):
        self.authorize()

        url = self._build_url('/b2api/v1/b2_get_upload_url')
        headers = {'Authorization': self.authorization_token}
        params = {'bucketId': self.bucket_id}
        return requests.get(url, headers=headers, params=params).json()

    def _build_url(self, endpoint=None, authorization=True):
        return "%s%s" % (self.base_url, endpoint)

    def upload_file(self, name, content):
        self.authorize()

        response = self.get_upload_url()
        if 'uploadUrl' not in response:
            return False

        url = response['uploadUrl']
        content.seek(0)
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
        # Status is 503: Service unavailable. Try again
        if download_response.status_code == 503:
            attempts = 0
            while attempts <= 3 and download_response.status_code == 503:
                download_response = requests.post(url, headers=headers, data=content.read())
                attempts += 1
        if download_response.status_code != 200:
            raise BackBlazeB2.APIError('{} error while uploading file to B2 Cloud. Response: {}'.format(download_response.status_code, download_response.content))

        return download_response.json()

    def get_file_info(self, name):
        self.authorize()

        headers = {'Authorization': self.authorization_token}
        return requests.get("%s/file/%s/%s" % (self.download_url, self.bucket_name, name), headers=headers)

    def file_download_url(self, name):
        self.authorize()

        return "%s/file/%s/%s" % (self.download_url, self.bucket_name, name)

    def download_file(self, name):
        headers = {}

        if self.bucket_private:
            headers = {'Authorization': self.authorization_token}

        return requests.get(self.file_download_url(name), headers=headers).content

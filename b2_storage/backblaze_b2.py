# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import base64
import datetime
import hashlib
import logging
import six

import requests

log = logging.getLogger(__name__)


class BackBlazeB2(object):
    class APIError(Exception):
        pass

    def __init__(self, app_key=None, account_id=None, bucket_name=None, bucket_private=False, bucket_id=None):
        self.bucket_id = bucket_id
        self.account_id = account_id
        self.app_key = app_key
        self.bucket_name = bucket_name
        self.bucket_private = bucket_private

        self.last_authorized = None
        self.last_auth_failed = None
        self._authorization_token = None
        
        self.authorize()
        if not self.bucket_id:
            self.get_bucket_id_by_name()

    @property
    def authorization_token(self):
        self.authorize()
        return self._authorization_token

    def authorize(self):
        # Refresh token every 12h
        if self.last_authorized and datetime.datetime.now() < (self.last_authorized + datetime.timedelta(hours=12)):
            return True

        # In case of failure, repeat every 10 secs
        if self.last_auth_failed and datetime.datetime.now() < (self.last_auth_failed + datetime.timedelta(seconds=10)):
            return False

        headers = {'Authorization': 'Basic: %s' % (
            base64.b64encode(('%s:%s' % (self.account_id, self.app_key)).encode('utf-8'))).decode('utf-8')}

        try:
            response = requests.get('https://api.backblaze.com/b2api/v1/b2_authorize_account', headers=headers,
                                    timeout=2)
            if response.status_code == 200:
                resp = response.json()
                self.base_url = resp['apiUrl']
                self.download_url = resp['downloadUrl']
                self._authorization_token = resp['authorizationToken']
                self.last_authorized = datetime.datetime.now()

                return True
            else:
                return False
        except requests.exceptions.Timeout:
            self.last_auth_failed = datetime.datetime.now()
            log.error('Connection to backblaze timeouted during authorization')
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
        file_content = content.read()
        content.seek(0)

        if isinstance(file_content, six.string_types):
            file_content = file_content.encode("utf-8")

        sha1_of_file_data = hashlib.sha1(file_content).hexdigest()

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
            raise BackBlazeB2.APIError(
                '{} error while uploading file to B2 Cloud. Response: {}'.format(download_response.status_code,
                                                                                 download_response.content))

        return download_response.json()

    def get_file_info(self, name):
        self.authorize()

        headers = {'Authorization': self.authorization_token}
        return requests.get("%s/file/%s/%s" % (self.download_url, self.bucket_name, name), headers=headers)

    def download_file(self, name):
        headers = {}

        if self.bucket_private:
            headers = {'Authorization': self.authorization_token}

        return requests.get(self.get_file_url(name), headers=headers).content

    def get_file_url(self, name):
        self.authorize()

        return "%s/file/%s/%s" % (self.download_url, self.bucket_name, name)

    def get_bucket_id_by_name(self):
        """
        BackBlaze B2 should  make an endpoint to retrieve buckets by its name.
        """
        headers = {'Authorization': self.authorization_token}
        params = {'accountId': self.account_id}
        resp = requests.get(self._build_url("/b2api/v1/b2_list_buckets"), headers=headers, params=params).json()
        if 'buckets' in resp:
            buckets = resp['buckets']
            for bucket in buckets:
                if bucket['bucketName'] == self.bucket_name:
                    self.bucket_id = bucket['bucketId']
                    return True

        else:
            return False

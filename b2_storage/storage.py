# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from tempfile import TemporaryFile

from io import BytesIO
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import File
from .backblaze_b2 import BackBlazeB2
import re
import os
from uuid import uuid4

class B2Storage(Storage):
    def __init__(self, account_id=None, app_key=None, bucket_name=None, bucket_id=None):
        self.account_id = settings.BACKBLAZEB2_ACCOUNT_ID if account_id == None else account_id
        self.app_key = settings.BACKBLAZEB2_APP_KEY if app_key == None else app_key
        self.bucket_name = settings.BACKBLAZEB2_BUCKET_NAME if bucket_name == None else bucket_name
        self.bucket_id = settings.BACKBLAZEB2_BUCKET_ID if bucket_id == None else bucket_id
        self.b2 = BackBlazeB2(app_key=self.app_key, account_id=self.account_id, bucket_name=self.bucket_name, bucket_id=self.bucket_id)

    def save(self, name, content, max_length=None):
        """
        Save and retrieve the filename.
        If the file exists it will make another version of that file.
        """

        name = re.sub("^./", "", name)

        folder_path = os.path.dirname(name)
        extension = os.path.splitext(name)[1]

        if extension:
            newname = "{}{}".format(uuid4(), extension)
        else:
            newname = "{}".format(uuid4())

        name = os.path.join(folder_path, newname)

        resp = self.b2.upload_file(name, content)
        if 'fileName' in resp:
            return resp['fileName']
        else:
            # Raise exception
            pass

    def exists(self, name):
        '''
        BackBlaze B2 does not have a method to retrieve a filename info.
        To get the info you need to make a download request, it will request the whole body.
        imagine a file of 1 GB to only get the file info.
        you can also list all files in that directory in chunks of 1000 imagine a directory of 10000.
        For now it will only request return False.
        '''

        return False

    def _temporary_storage(self, contents):
        '''
        Use this to return file objects
        '''

        conent_file = TemporaryFile(contents, 'r+')
        return conent_file

    def open(self, name, mode='rb'):
        resp = self.b2.download_file(name)

        output = BytesIO()
        output.write(resp)
        output.seek(0)
        return File(output, name)


    #
    # def get_available_name(self, name, max_length=None):
    #     pass
    #
    # def delete(self, name):
    #     pass
    #
    # def exists(self, name):
    #     pass
    #
    # def listdir(self, path):
    #     pass

    def size(self, name):
        return 1

    def url(self, name):
        return "{}/file/{}/{}".format(self.b2.download_url, self.b2.bucket_name, name)

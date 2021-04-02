import boto3
import botocore
import threading
import time
from loguru import logger

class client(object):
    def __init__(self, region_name=None, aws_access_key_id=None,
                    aws_secret_access_key=None, aws_session_token=None, **kwargs):

        if not region_name:
            self._region_name = input('Region name: ')
        else:
            self._region_name = region_name

        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token

    def _get_client(self, service):
        try:
            # If credentials are being passed through, use them
            if not self._aws_access_key_id and not self._aws_secret_access_key:
                session = boto3.session.Session(region_name=self._region_name)
            # Default to local credentials
            else:
                session = boto3.session.Session(
                    region_name=self._region_name,
                    aws_access_key_id=self._aws_access_key_id,
                    aws_secret_access_key=self._aws_secret_access_key,
                    aws_session_token=self._aws_session_token
                )

            self._name = session.client('iam').list_account_aliases()['AccountAliases'][0]
            self._number = session.client('sts').get_caller_identity().get('Account')

            return(session.client(service))
        except:
            raise('Error creating client.')
            exit(1)

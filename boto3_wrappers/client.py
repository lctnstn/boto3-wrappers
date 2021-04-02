import boto3
import botocore
import threading
import time
from loguru import logger

class client(object):
    def __init__(self, **kwargs):
        self._name = kwargs['name']
        self._number = kwargs['number']
        self._ignore_drift = kwargs['ignore_drift']
        self._client = kwargs['client']

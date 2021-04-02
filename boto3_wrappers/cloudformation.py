import boto3
import botocore
import threading
import time
from loguru import logger

class cloudformation:
    def __init__(self, **kwargs):
        self._name = kwargs['name']
        self._number = kwargs['number']
        self._ignore_drift = kwargs['ignore_drift']
        self._client = kwargs['client']

    def __del__(self):
        logger.debug(f'{self._name} complete')

    def create_update(self, **kwargs):
        # First try to create the stack new.
        try:
            create_stack = self._client.create_stack(
                StackName=kwargs['stack'],
                TemplateBody=kwargs['template'],
                Parameters=kwargs['cli_input']['Parameters'],
                Tags=kwargs['cli_input']['Tags'],
                Capabilities=kwargs['capabilities'],
            )

            # Thread the status checker
            self._stack_id=create_stack['StackId']
            self._thread = threading.Thread(target=self.__check_create_update)
            self._thread.start()
            logger.info(f'Creating stack in {self._name}')

        except botocore.exceptions.ClientError as create_error:
            # The AlreadyExistsException shows when a stack with the same name already exists, begin update process.
            if create_error.response['Error']['Code'] == 'AlreadyExistsException':
                # Detect drift in stack before updating.
                detect_drift = self._client.detect_stack_drift(StackName=kwargs['stack'])
                drift_detect_id = detect_drift["StackDriftDetectionId"]
                drift_detect_status = ""
                while drift_detect_status not in ["DETECTION_COMPLETE", "DETECTION_FAILED"]:
                    check_drift_detect_status = self._client.describe_stack_drift_detection_status(StackDriftDetectionId=drift_detect_id)
                    drift_detect_status = check_drift_detect_status["DetectionStatus"]
                    time.sleep(1) # Avoid throttling
                # If there is no drift or if we're ignoring drift, proceed with update,
                if check_drift_detect_status['StackDriftStatus'] == 'IN_SYNC' or (check_drift_detect_status['StackDriftStatus'] == 'DRIFTED' and self._ignore_drift):
                    if not self._ignore_drift:
                        logger.info(f'No drift detected in {self._name}')
                    try:
                        update_stack = self._client.update_stack(
                            StackName=kwargs['stack'],
                            TemplateBody=kwargs['template'],
                            Parameters=kwargs['cli_input']['Parameters'],
                            Tags=kwargs['cli_input']['Tags'],
                            Capabilities=kwargs['capabilities']
                        )

                        # Thread the status checker
                        self._stack_id=update_stack['StackId']
                        self._thread = threading.Thread(target=self.__check_create_update)
                        self._thread.start()
                        logger.info(f'Updating stack in {self._name}')

                    except botocore.exceptions.ClientError as update_error:
                        if update_error.response['Error']['Code'] == 'ValidationError':
                            # A stack that doesn't differ from template in update will throw a ValidationError with the message below.
                            if update_error.response['Error']['Message'] == 'No updates are to be performed.':
                                # This isn't a problem, the update is skipped
                                logger.info(f'No updates to be performed in {self._name}')
                        else:
                            # Any other errors are problematic, too.
                            logger.error(f'Error in {self._name} - {update_error.response["Error"]["Code"]} - {update_error.response["Error"]["Message"]}')
                else:
                    # If there is drift is detected that's a problem, don't update the stack.
                    if check_drift_detect_status['StackDriftStatus'] == 'DRIFTED':
                        logger.warning(f'Drift detected in {self._name} - skipping update')
                    # If we get another response code from drift detection, we've got a problem.
                    else:
                        logger.warning(f'Unhandled drift status in {self._name} - {check_drift_detect_status["StackDriftStatus"]}')
            else:
                # Any other create_stack errors are problems.
                logger.error(f'Unhandled create error in {self._name} - {create_error.response["Error"]["Code"]} - {create_error.response["Error"]["Message"]}')

    def __check_create_update(self):
        stack_status = ""
        # Any of these status returns means we need to wait and check again.
        while stack_status in ["", 'CREATE_IN_PROGRESS', 'ROLLBACK_IN_PROGRESS', 'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS']:
            describe = self._client.describe_stacks(StackName=self._stack_id)
            stack_status = describe['Stacks'][0]['StackStatus']
            time.sleep(5) # Avoid throttling

        # Any of these status returns are good.
        if stack_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            logger.info(f'{self._name} - {stack_status}')

        # Any of these status returns result in an error.
        if stack_status in ['CREATE_FAILED', 'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE']:
            logger.error(f'{self._name} - {stack_status}')

    def delete(self, **kwargs):
        # See if the stack exists
        try:
            find_stack = self._client.describe_stacks(
                StackName=kwargs['stack']
            )
            if find_stack['Stacks']:
                stack_id = find_stack['Stacks'][0]['StackId']
                logger.info(f'Deleting {kwargs["stack"]} from {self._name}')
                delete_stack = self._client.delete_stack(
                    StackName=kwargs['stack']
                )
                self._stack_id=stack_id
                self._thread = threading.Thread(target=self.__check_delete)
                self._thread.start()
        except botocore.exceptions.ClientError as delete_error:
            logger.info(f'{kwargs["stack"]} not in {self._name}')

    def __check_delete(self):
        stack_status = ""
        # Look through all stacks
        while stack_status in ["", 'DELETE_IN_PROGRESS']:
            paginator = self._client.get_paginator('list_stacks')
            pages = paginator.paginate()
            for page in pages:
                for stack in page['StackSummaries']:
                    if stack['StackId'] == self._stack_id:
                        stack_status = stack['StackStatus']
                        if 'StackStatusReason' in stack.keys():
                            status_reason = stack['StackStatusReason']
            time.sleep(5) # Avoid throttling
        if stack_status == 'DELETE_COMPLETE':
            logger.info(f'{self._name} - {stack_status}')
        else:
            logger.error(f'{self._name} - {stack_status} - {status_reason}')

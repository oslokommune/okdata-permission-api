import os
import json
from datetime import datetime

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder

from okdata.aws.logging import logging_wrapper, log_add
from dataplatform_keycloak.resource_server import ResourceServer


BACKUP_BUCKET_NAME = os.environ["BACKUP_BUCKET_NAME"]
BACKUP_BUCKET_PREFIX = os.environ["SERVICE_NAME"]
KEYCLOAK_MAX_ITEMS_PER_PAGE = 100

patch_all()


@logging_wrapper
@xray_recorder.capture("backup_permissions")
def backup_permissions(event, context):
    """Get all permissions and save to S3."""
    permissions = list(get_all_permissions())

    log_add(num_permissions=len(permissions))

    if not permissions:
        return

    write_to_s3(permissions)


def get_all_permissions():
    """Generator that yields permissions."""
    resource_server = ResourceServer()

    current_index = 0
    permissions = resource_server.list_permissions(
        first=current_index, max_result=KEYCLOAK_MAX_ITEMS_PER_PAGE
    )
    while len(permissions) > 0:
        for permission in permissions:
            current_index += 1
            yield permission
        permissions = resource_server.list_permissions(
            first=current_index, max_result=KEYCLOAK_MAX_ITEMS_PER_PAGE
        )


def write_to_s3(permissions_data):
    """Dump permissions data to S3."""
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    dt_now = datetime.utcnow()
    file_name = f"{dt_now.isoformat()}_permissions.json".replace(":", "-")
    backup_object_key = (
        f"{BACKUP_BUCKET_PREFIX}/{dt_now.year}/{dt_now.month}/{file_name}"
    )

    log_add(backup_object_key=backup_object_key)

    s3.put_object(
        Body=str(json.dumps(permissions_data)),
        Bucket=BACKUP_BUCKET_NAME,
        Key=backup_object_key,
    )

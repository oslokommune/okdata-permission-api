import os
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder
from okdata.aws.logging import logging_wrapper, log_add

from dataplatform_keycloak.resource_server import ResourceServer


BACKUP_BUCKET_NAME = os.environ["BACKUP_BUCKET_NAME"]
BACKUP_BUCKET_PREFIX = os.environ["SERVICE_NAME"]

patch_all()


@logging_wrapper
@xray_recorder.capture("backup_permissions")
def backup_permissions(event, context):
    """Get all permissions and save to S3."""
    permissions = ResourceServer().list_permissions()

    log_add(num_permissions=len(permissions))

    if permissions:
        write_to_s3(permissions)


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


def load_latest_backup(max_age_in_weeks=12):
    """Load last permissions backup file from S3."""
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    max_age = timedelta(weeks=max_age_in_weeks)
    dt_now = datetime.utcnow()
    lookup_dt = dt_now
    backup_key = None

    log_add(backup_object_max_age=(dt_now - max_age).isoformat())

    while not backup_key:
        lookup_prefix = BACKUP_BUCKET_PREFIX + "/{}/{}/".format(
            lookup_dt.year,
            lookup_dt.month,
        )
        lookup_dt = lookup_dt - relativedelta(months=1)

        if (dt_now - lookup_dt) > max_age:
            break

        response = s3.list_objects_v2(
            Bucket=BACKUP_BUCKET_NAME,
            Prefix=lookup_prefix,
        )
        object_keys = [
            object_metadata["Key"] for object_metadata in response.get("Contents", [])
        ]

        if len(object_keys) > 0:
            backup_key = sorted(object_keys, reverse=True)[0]

    log_add(backup_latest_object_key=backup_key)

    if not backup_key:
        return None

    obj = s3.get_object(Bucket=os.environ["BACKUP_BUCKET_NAME"], Key=backup_key)
    permissions = json.loads(obj["Body"].read())

    log_add(backup_latest_permissions_count=len(permissions))

    return permissions

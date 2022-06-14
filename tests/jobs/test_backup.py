import json
import os
import unittest
from datetime import datetime

import boto3
from freezegun import freeze_time

from dataplatform_keycloak.resource_server import ResourceServer
from jobs.backup import (
    BACKUP_BUCKET_NAME,
    BACKUP_BUCKET_PREFIX,
    backup_permissions,
    load_latest_backup,
)
from models import User
from tests.setup import populate_local_keycloak


def _prefix_from_datetime(backup_datetime):
    return "{}/{}/{}/{}_permissions.json".format(
        BACKUP_BUCKET_PREFIX,
        backup_datetime.year,
        backup_datetime.month,
        backup_datetime.isoformat().replace(":", "-"),
    )


def test_backup_permissions(mock_ssm_client, mock_s3_bucket):
    populate_local_keycloak.populate()
    rs = ResourceServer()
    janedoe_user = User.parse_obj({"user_id": "janedoe", "user_type": "user"})
    rs.create_resource("okdata:dataset:test-dataset", owner=janedoe_user)
    rs.create_resource("okdata:dataset:test-dataset2", owner=janedoe_user)

    backup_permissions({}, {})

    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    key = s3.list_objects_v2(Bucket=BACKUP_BUCKET_NAME)["Contents"][0]["Key"]
    obj = s3.get_object(Bucket=BACKUP_BUCKET_NAME, Key=key)
    backed_up_permissions = json.loads(obj["Body"].read())

    case = unittest.TestCase()
    case.assertCountEqual(backed_up_permissions, rs.list_permissions())


def test_s3_prefixes(mock_s3_bucket, permission_backups):
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    object_keys = [
        obj["Key"] for obj in s3.list_objects_v2(Bucket=BACKUP_BUCKET_NAME)["Contents"]
    ]

    assert set(object_keys) == set(
        [
            _prefix_from_datetime(datetime.fromisoformat(date))
            for date, _ in permission_backups
        ]
    )


def test_load_latest_backup(mock_s3_bucket, permission_backups):
    with freeze_time("2022-05-25T12:00:00+00:00"):
        permissions = load_latest_backup()
    assert len(permissions) == 2


def test_load_latest_backup_none_within_max_age(mock_s3_bucket, permission_backups):
    with freeze_time("2022-8-26T17:00:00+00:00"):
        permissions = load_latest_backup(max_age_in_weeks=4)
    assert permissions is None

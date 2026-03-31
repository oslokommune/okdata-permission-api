import json
import os
import unittest
from datetime import datetime

import boto3
from freezegun import freeze_time
from moto import mock_aws

from dataplatform_keycloak.resource_server import ResourceServer
from jobs.backup import (
    BACKUP_BUCKET_NAME,
    BACKUP_BUCKET_PREFIX,
    backup_permissions,
    load_latest_backup,
    write_to_s3,
)
from models import User
from tests.setup import populate_local_keycloak


def _mock_s3():
    s3 = boto3.resource("s3", region_name=os.environ["AWS_REGION"])
    s3.create_bucket(
        Bucket=os.environ["BACKUP_BUCKET_NAME"],
        CreateBucketConfiguration={"LocationConstraint": os.environ["AWS_REGION"]},
    )


def _write_permission_backups():
    permission_backups = [
        ("2022-05-24T10:00:30", [{"foo": "bar"}, {"abc": "def"}]),
        ("2022-05-12T11:00:30", [{"foo": "bar"}]),
        ("2022-03-01T11:00:30", [{"foo": "bar"}]),
        ("2021-07-01T12:00:30", [{"foo": "bar"}]),
        ("2022-01-01T13:00:30", [{"foo": "bar"}]),
    ]

    for date, permissions in permission_backups:
        with freeze_time(date):
            write_to_s3(permissions)

    return permission_backups


def _prefix_from_datetime(backup_datetime):
    return "{}/{}/{}/{}_permissions.json".format(
        BACKUP_BUCKET_PREFIX,
        backup_datetime.year,
        backup_datetime.month,
        backup_datetime.isoformat().replace(":", "-"),
    )


@mock_aws
def test_backup_permissions(mock_ssm_client):
    _mock_s3()
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


@mock_aws
def test_s3_prefixes():
    _mock_s3()
    permission_backups = _write_permission_backups()

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


@mock_aws
def test_load_latest_backup():
    _mock_s3()
    _write_permission_backups()

    with freeze_time("2022-05-25T12:00:00+00:00"):
        permissions = load_latest_backup()
    assert len(permissions) == 2


@mock_aws
def test_load_latest_backup_none_within_max_age():
    _mock_s3()
    _write_permission_backups()

    with freeze_time("2022-8-26T17:00:00+00:00"):
        permissions = load_latest_backup(max_age_in_weeks=4)
    assert permissions is None

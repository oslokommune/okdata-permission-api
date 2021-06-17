import json
import os
import unittest

import boto3
import pytest
from freezegun import freeze_time
from moto import mock_s3

import backup.handler as handler
from dataplatform_keycloak.resource_server import ResourceServer
from models import User
from tests.setup import populate_local_keycloak


@pytest.fixture(scope="function")
def mock_s3_bucket():
    mock_s3().start()
    s3 = boto3.resource("s3", region_name=os.environ["AWS_REGION"])
    s3.create_bucket(
        Bucket=os.environ["BACKUP_BUCKET_NAME"],
        CreateBucketConfiguration={"LocationConstraint": os.environ["AWS_REGION"]},
    )


def test_backup_permissions(mock_ssm_client, mock_s3_bucket):
    populate_local_keycloak.populate()
    rs = ResourceServer()
    janedoe_user = User.parse_obj({"user_id": "janedoe", "user_type": "user"})
    rs.create_resource("okdata:dataset:test-dataset", owner=janedoe_user)
    rs.create_resource("okdata:dataset:test-dataset2", owner=janedoe_user)

    handler.backup_permissions({}, {})

    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    key = s3.list_objects_v2(Bucket=os.environ["BACKUP_BUCKET_NAME"])["Contents"][0][
        "Key"
    ]
    obj = s3.get_object(Bucket=os.environ["BACKUP_BUCKET_NAME"], Key=key)
    backed_up_permissions = json.loads(obj["Body"].read())

    case = unittest.TestCase()
    case.assertCountEqual(backed_up_permissions, rs.list_permissions())


def test_s3_prefixes(mock_s3_bucket):
    backup_dates = [
        "2021-05-01T10:00:30+00:00",
        "2021-05-05T11:00:30+00:00",
        "2021-07-01T12:00:30+00:00",
        "2022-01-01T13:00:30+00:00",
    ]

    for date in backup_dates:
        with freeze_time(date):
            handler.write_to_s3({"foo": "bar"})

    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    object_keys = [
        obj["Key"]
        for obj in s3.list_objects_v2(Bucket=os.environ["BACKUP_BUCKET_NAME"])[
            "Contents"
        ]
    ]
    assert object_keys == [
        f"{handler.BACKUP_BUCKET_PREFIX}/2021/5/2021-05-01T10-00-30_permissions.json",
        f"{handler.BACKUP_BUCKET_PREFIX}/2021/5/2021-05-05T11-00-30_permissions.json",
        f"{handler.BACKUP_BUCKET_PREFIX}/2021/7/2021-07-01T12-00-30_permissions.json",
        f"{handler.BACKUP_BUCKET_PREFIX}/2022/1/2022-01-01T13-00-30_permissions.json",
    ]

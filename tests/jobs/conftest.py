import os

import boto3
import pytest
from freezegun import freeze_time
from moto import mock_s3

from jobs.backup import write_to_s3


@pytest.fixture
def mock_s3_bucket():
    mock_s3().start()
    s3 = boto3.resource("s3", region_name=os.environ["AWS_REGION"])
    s3.create_bucket(
        Bucket=os.environ["BACKUP_BUCKET_NAME"],
        CreateBucketConfiguration={"LocationConstraint": os.environ["AWS_REGION"]},
    )


@pytest.fixture
def permission_backups(mock_s3_bucket):
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

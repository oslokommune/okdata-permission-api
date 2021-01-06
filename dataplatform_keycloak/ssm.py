import os
import boto3


class SsmClient:
    def __init__(self):
        self.client = boto3.client("ssm", region_name=os.environ["AWS_REGION"])

    def get_secret(self, key):
        resp = self.client.get_parameter(Name=key, WithDecryption=True)
        return resp["Parameter"]["Value"]

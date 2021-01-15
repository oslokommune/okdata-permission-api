import os
import boto3


class SsmClient:
    @staticmethod
    def get_secret(key):
        client = boto3.client("ssm", region_name=os.environ["AWS_REGION"])
        resp = client.get_parameter(Name=key, WithDecryption=True)
        return resp["Parameter"]["Value"]

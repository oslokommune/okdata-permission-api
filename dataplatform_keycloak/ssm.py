import boto3

client = boto3.client("ssm", region_name="eu-west-1")


def get_secret(key):
    resp = client.get_parameter(Name=key, WithDecryption=True)
    return resp["Parameter"]["Value"]

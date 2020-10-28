import json


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset-id"]
    version = event["pathParameters"]["version"]
    return {"statusCode": 200, "body": json.dumps({"message": "Ok"})}

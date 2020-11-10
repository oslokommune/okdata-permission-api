import json


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset_id"]
    return {"statusCode": 200, "body": json.dumps({"dataset_id": dataset_id})}

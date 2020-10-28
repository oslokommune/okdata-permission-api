import json


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset-id"]
    content = json.loads(event["body"])
    updated = content.update({"dataset_id": dataset_id})
    return {"statusCode": 200, "body": json.dumps(updated)}

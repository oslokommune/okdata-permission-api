import json


def handle(event, context):
    body = json.loads(event["body"])
    return {"statusCode": 201, "body": json.dumps(body)}

import json
import uuid


def handle(event, context):
    body = json.loads(event["body"])
    try:
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "upload_url": f"s3://{uuid.uuid4()}/{body['editionId']}/{body['filename']}"
                }
            ),
        }
    except Exception:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid request body"}),
        }

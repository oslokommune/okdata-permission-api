import json
import uuid


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset"]
    version = event["pathParameters"]["version"]
    return {
        "statusCode": 200,
        "body": json.dumps(
            {"download_url": f"s3://{uuid.uuid4()}/{dataset_id}/{version}"}
        ),
    }

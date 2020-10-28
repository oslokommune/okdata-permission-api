import json


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset-id"]
    version = event["pathParameters"]["version"]
    return {
        "statusCode": 201,
        "body": json.dumps({"event_stream_id": f"{dataset_id}/{version}"}),
    }

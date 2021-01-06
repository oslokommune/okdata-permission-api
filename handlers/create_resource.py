import json
from dataplatform_keycloak import ResourceServer

resource_server = ResourceServer()


def handle(event, context):
    body = json.loads(event["body"])
    team = body["team"]
    dataset_id = body["dataset_id"]
    resource_server.create_dataset_resource(dataset_id, owner=team)
    return {"statusCode": 201, "body": json.dumps({"message": "Created"})}

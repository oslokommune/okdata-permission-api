import json
from dp_keycloak.resource_manager import ResourceServer, ResourceScopes


auth_client = ResourceServer()


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset-id"]
    version = event["pathParameters"]["version"]
    principal_id = event["requestContext"]["authorizer"]["principalId"]
    if not auth_client.evaluate(dataset_id, ResourceScopes.update, principal_id):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"{principal_id} not authorized for {ResourceScopes.update.value} on {dataset_id}"
                }
            ),
        }
    return {
        "statusCode": 201,
        "body": json.dumps({"event_stream_id": f"{dataset_id}/{version}"}),
    }

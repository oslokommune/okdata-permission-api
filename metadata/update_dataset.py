import json
from dp_keycloak.resource_manager import ResourceServer, ResourceScopes

resource_server = ResourceServer()


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset-id"]
    principal_id = event["requestContext"]["authorizer"]["principalId"]
    if not resource_server.evaluate(dataset_id, ResourceScopes.update, principal_id):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"{principal_id} not authorized for {ResourceScopes.update.value} on {dataset_id}"
                }
            ),
        }
    content = json.loads(event["body"])
    updated = content.update({"dataset_id": dataset_id})
    return {"statusCode": 200, "body": json.dumps(updated)}

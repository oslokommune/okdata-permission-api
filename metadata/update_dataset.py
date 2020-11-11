import json
from dp_keycloak.resource_manager import ResourceScope
from dp_keycloak.resource_authorizer import ResourceAuthorizer

auth_client = ResourceAuthorizer()


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset_id"]
    principal_id = event["requestContext"]["authorizer"]["principalId"]
    user_token = event["headers"]["Authorization"].split(" ")[-1]
    if not auth_client.has_access(dataset_id, ResourceScope.update, user_token):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"{principal_id} not authorized for {ResourceScope.update.value} on {dataset_id}"
                }
            ),
        }
    content = json.loads(event["body"])
    updated = content.update({"dataset_id": dataset_id})
    return {"statusCode": 200, "body": json.dumps(updated)}

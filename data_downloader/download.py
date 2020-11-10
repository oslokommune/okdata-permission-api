import json
import uuid
from dp_keycloak.resource_manager import ResourceServer, ResourceScopes

auth_client = ResourceServer()


def handle(event, context):
    dataset_id = event["pathParameters"]["dataset_id"]
    version = event["pathParameters"]["version"]
    principal_id = event["requestContext"]["authorizer"]["principalId"]

    if not auth_client.evaluate(dataset_id, ResourceScopes.read, principal_id):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"User {principal_id} not authorized for {ResourceScopes.read.value} on "
                }
            ),
        }
    return {
        "statusCode": 200,
        "body": json.dumps(
            {"download_url": f"s3://{uuid.uuid4()}/{dataset_id}/{version}"}
        ),
    }

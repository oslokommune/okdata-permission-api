import json
import uuid
from dp_keycloak.resource_manager import ResourceServer, ResourceScopes

auth_client = ResourceServer()


def handle(event, context):
    body = json.loads(event["body"])
    dataset_id = body["editionIn"].split("/")[0]
    principal_id = event["requestContext"]["authorizer"]["principalId"]
    if not auth_client.evaluate(dataset_id, ResourceScopes.write, principal_id):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"User {principal_id} not authorized for {ResourceScopes.write.value} on "
                }
            ),
        }

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "upload_url": f"s3://{uuid.uuid4()}/{body['editionId']}/{body['filename']}"
            }
        ),
    }

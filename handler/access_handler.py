import json
from dataplatform_keycloak import ResourceAuthorizer, ResourceServer, ResourceScope


auth_client = ResourceAuthorizer()
resource_server = ResourceServer()


def handle(event, context):

    dataset_id = event["pathParameters"]["dataset_id"]
    principal_id = event["requestContext"]["authorizer"]["principalId"]
    user_token = event["headers"]["Authorization"].split(" ")[-1]

    if not auth_client.has_access(dataset_id, ResourceScope.owner, user_token):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"User {principal_id} not authorized for {ResourceScope.owner.value} on {dataset_id}"
                }
            ),
        }

    body = json.loads(event["body"])
    scope = ResourceScope(body["scope"])
    team = body.get("team", None)
    username = body.get("username", None)

    if team or username:
        updated_permission = resource_server.update_permission(
            resource_name=dataset_id,
            scope=scope,
            group_to_add=team,
            user_to_add=username,
        )

    return {
        "statusCode": 200,
        "body": json.dumps(updated_permission),
    }


def list_permissions(event, context):
    dataset_id = event["pathParameters"]["dataset_id"]
    principal_id = event["requestContext"]["authorizer"]["principalId"]
    user_token = event["headers"]["Authorization"].split(" ")[-1]

    if not auth_client.has_access(dataset_id, ResourceScope.owner, user_token):
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"User {principal_id} not authorized for {ResourceScope.owner.value} on {dataset_id}"
                }
            ),
        }

    permissions = resource_server.list_permissions(resource_name=dataset_id)

    return {
        "statusCode": 200,
        "body": json.dumps(permissions),
    }

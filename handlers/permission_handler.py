import json
from dataplatform_keycloak import ResourceAuthorizer, ResourceServer
from models import ResourceScope, OkdataPermission


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
    query_parameters = (
        {} if not event["queryStringParameters"] else event["queryStringParameters"]
    )
    dataset_id = query_parameters.get("dataset_id", None)
    team_id = query_parameters.get("team_id", None)
    scope = query_parameters.get("scope", None)
    first = query_parameters.get("first", None)
    max_result = query_parameters.get("max", None)

    try:
        if scope:
            scope = ResourceScope(scope)
    except Exception:
        error_msg = (
            f"Invalid scope value {scope}. Must be one of {ResourceScope.list_values()}"
        )
        return {"statusCode": 400, "body": json.dumps({"message": error_msg})}

    uma_permissions = resource_server.list_permissions(
        resource_name=dataset_id,
        group=team_id,
        scope=scope,
        first=first,
        max_result=max_result,
    )

    return {
        "statusCode": 200,
        "body": json.dumps(to_okdata_permissions(uma_permissions)),
    }


def to_okdata_permissions(uma_permissions):
    return [
        OkdataPermission(
            dataset_id=uma_permission["name"].split(":")[0],
            description=uma_permission["description"],
            scopes=uma_permission["scopes"],
            teams=[group[1:] for group in uma_permission.get("groups", [])],
            users=uma_permission.get("users", []),
            clients=uma_permission.get("clients", []),
        ).dict()
        for uma_permission in uma_permissions
    ]

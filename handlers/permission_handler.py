import json
from dataplatform_keycloak import ResourceAuthorizer, ResourceServer
from models import ResourceScope, OkdataPermission, UpdatePermissionBody
from pydantic import ValidationError


auth_client = ResourceAuthorizer()
resource_server = ResourceServer()


def update_permissions(event, context):

    dataset_id = event["pathParameters"]["dataset_id"]
    user_token = event["headers"]["Authorization"].split(" ")[-1]

    if not auth_client.has_access(dataset_id, ResourceScope.owner, user_token):
        principal_id = event["requestContext"]["authorizer"]["principalId"]
        return {
            "statusCode": 403,
            "body": json.dumps(
                {
                    "message": f"User {principal_id} not authorized for {ResourceScope.owner.value} on {dataset_id}"
                }
            ),
        }

    try:
        body = UpdatePermissionBody(**json.loads(event["body"]))
    except ValidationError:
        # TODO: log exception
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid body"})}

    updated_permission = resource_server.update_permission(
        resource_name=dataset_id,
        scope=body.scope,
        add_users=body.add_users,
        remove_users=body.remove_users,
    )

    return {
        "statusCode": 200,
        "body": json.dumps(to_ok_data_permission(updated_permission)),
    }


# TODO: Find out if this information should be open to all logged in users
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

    ok_data_permissions = [
        to_ok_data_permission(permission) for permission in uma_permissions
    ]

    return {
        "statusCode": 200,
        "body": json.dumps(ok_data_permissions),
    }


def to_ok_data_permission(uma_permission):
    return OkdataPermission(
        dataset_id=uma_permission["name"].split(":")[0],
        description=uma_permission["description"],
        scopes=uma_permission["scopes"],
        teams=[group[1:] for group in uma_permission.get("groups", [])],
        users=uma_permission.get("users", []),
        clients=uma_permission.get("clients", []),
    ).dict()

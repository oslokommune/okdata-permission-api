import json
from dp_keycloak.resource_manager import ResourceScope
from dp_keycloak.resource_authorizer import ResourceAuthorizer

auth_client = ResourceAuthorizer()


def handle(event, context):
    user_token = event["headers"]["Authorization"].split(" ")[-1]
    owner_permissions = auth_client.get_user_permissions(
        user_bearer_token=user_token, scope=ResourceScope.owner
    )

    my_datasets = [permission["rsname"] for permission in owner_permissions]

    return {"statusCode": 200, "body": json.dumps(my_datasets)}

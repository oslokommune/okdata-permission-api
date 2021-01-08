import json
import pytest
from keycloak import KeycloakOpenID

from dataplatform_keycloak import ResourceAuthorizer
from models import ResourceScope
from tests.setup import local_keycloak_config as kc_config

dataset_id = "integration-test-dataset"
resource_authorizer = ResourceAuthorizer()


class TestOkdataPermissionApi:
    def test_create_resource(self, resource_handler):
        create_resource_event = lambda_event(
            body={
                "dataset_id": dataset_id,
                "owner": {
                    "user_id": kc_config.team_id,
                    "user_type": "team",
                },
            }
        )

        create_resource_response = resource_handler.create_resource(
            create_resource_event, {}
        )

        assert create_resource_response["statusCode"] == 201

    def test_list_permissions(self, permission_handler):
        list_permissions_for_team_event = lambda_event(
            query_params={"team_id": kc_config.team_id}
        )
        team_permissions_response = permission_handler.list_permissions(
            list_permissions_for_team_event, {}
        )
        team_permissions_response_body = json.loads(team_permissions_response["body"])
        assert team_permissions_response_body == [
            {
                "dataset_id": "integration-test-dataset",
                "description": "Allows for owner operations on dataset: integration-test-dataset",
                "scopes": ["okdata:dataset:owner"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "dataset_id": "integration-test-dataset",
                "description": "Allows for read on dataset: integration-test-dataset",
                "scopes": ["okdata:dataset:read"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "dataset_id": "integration-test-dataset",
                "description": "Allows for update on dataset: integration-test-dataset",
                "scopes": ["okdata:dataset:update"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "dataset_id": "integration-test-dataset",
                "description": "Allows for write on dataset: integration-test-dataset",
                "scopes": ["okdata:dataset:write"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
        ]

    def test_update_permission_forbidden(self, permission_handler):
        event = lambda_event(
            username=kc_config.homersimpson,
            path_params={"dataset_id": dataset_id},
        )
        response = permission_handler.update_permissions(event, {})
        assert response["statusCode"] == 403
        assert json.loads(response["body"]) == {
            "message": f"User {kc_config.homersimpson} not authorized for {ResourceScope.owner.value} on {dataset_id}"
        }

    def test_update_permission(self, permission_handler):

        assert not resource_authorizer.has_access(
            dataset_id,
            ResourceScope.read,
            get_bearer_token_for_user(kc_config.homersimpson),
        )

        event = lambda_event(
            username=kc_config.janedoe,
            path_params={"dataset_id": dataset_id},
            body={
                "add_users": [{"user_id": kc_config.homersimpson, "user_type": "user"}],
                "scope": ResourceScope.read.read.value,
            },
        )
        response = permission_handler.update_permissions(event, {})
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == {
            "dataset_id": "integration-test-dataset",
            "description": "Allows for read on dataset: integration-test-dataset",
            "scopes": ["okdata:dataset:read"],
            "teams": ["group1"],
            "users": ["homersimpson"],
            "clients": [],
        }

        assert resource_authorizer.has_access(
            dataset_id,
            ResourceScope.read,
            get_bearer_token_for_user(kc_config.homersimpson),
        )


@pytest.fixture
def resource_handler(mock_ssm_client):
    from handlers import resource_handler

    return resource_handler


@pytest.fixture
def permission_handler(mock_ssm_client):
    from handlers import permission_handler

    return permission_handler


def lambda_event(username=None, path_params=None, query_params=None, body=None):
    event = {}
    if username:
        event["headers"] = {
            "Authorization": f"Bearer {get_bearer_token_for_user(username)}"
        }
        event["requestContext"] = {"authorizer": {"principalId": username}}

    event["pathParameters"] = None
    if path_params:
        event["pathParameters"] = path_params

    event["queryStringParameters"] = None
    if query_params:
        event["queryStringParameters"] = query_params

    if body:
        event["body"] = json.dumps(body)

    return event


def get_bearer_token_for_user(username):
    token = KeycloakOpenID(
        realm_name=kc_config.realm_name,
        server_url=f"{kc_config.server_url}",
        client_id=kc_config.resource_server_id,
        client_secret_key=kc_config.resource_server_secret,
    ).token(username, "password")
    return token["access_token"]

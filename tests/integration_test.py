import json
import pytest
from tests.setup import local_keycloak_config

dataset_id = "integration-test-dataset"


class TestOkdataPermissionApi:
    def test_create_resource(self, resource_handler):
        create_resource_event = {
            "body": json.dumps(
                {
                    "dataset_id": dataset_id,
                    "owner_id": local_keycloak_config.team_id,
                    "owner_type": "team",
                }
            )
        }

        create_resource_response = resource_handler.create_resource(
            create_resource_event, {}
        )

        assert create_resource_response["statusCode"] == 201

    def test_list_permissions(self, permission_handler):
        list_permissions_for_team_event = {
            "queryStringParameters": {"team_id": local_keycloak_config.team_id}
        }
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


@pytest.fixture
def resource_handler(mock_ssm_client):
    from handlers import resource_handler

    return resource_handler


@pytest.fixture
def permission_handler(mock_ssm_client):
    from handlers import permission_handler

    return permission_handler

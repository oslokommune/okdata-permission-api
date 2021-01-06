import json
from tests.setup import local_keycloak_config

dataset_id = "integration-test-dataset"


def test_handlers(mock_ssm_client):
    import handlers.create_resource as create_resource_handler
    import handlers.permission_handler as access_handler

    # Create resource
    create_resource_event = {
        "body": json.dumps(
            {"dataset_id": dataset_id, "team": local_keycloak_config.team_id}
        )
    }

    create_resource_response = create_resource_handler.handle(create_resource_event, {})

    assert create_resource_response["statusCode"] == 201

    list_permissions_for_team_event = {
        "queryStringParameters": {"team_id": local_keycloak_config.team_id}
    }
    team_permissions_response = access_handler.list_permissions(
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

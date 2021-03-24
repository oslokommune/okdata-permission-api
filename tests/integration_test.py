import jwt
from keycloak import KeycloakOpenID

from dataplatform_keycloak import ResourceAuthorizer
from models import DatasetScope
from tests.setup import local_keycloak_config as kc_config

dataset_id = "integration-test-dataset"
resource_authorizer = ResourceAuthorizer()


class TestOkdataPermissionApi:
    def test_create_resource_forbidden(self, mock_client):
        body = {
            "dataset_id": dataset_id,
            "owner": {
                "user_id": kc_config.team_id,
                "user_type": "team",
            },
        }

        token = get_bearer_token_for_user(kc_config.janedoe)

        create_resource_response = mock_client.post(
            "/permissions", json=body, headers=auth_header(token)
        )
        assert create_resource_response.status_code == 403

    def test_create_resource(self, mock_client):

        body = {
            "dataset_id": dataset_id,
            "owner": {
                "user_id": kc_config.team_id,
                "user_type": "team",
            },
        }

        token = get_token_for_service()

        create_resource_response = mock_client.post(
            "/permissions", json=body, headers=auth_header(token)
        )
        assert create_resource_response.status_code == 201

    def test_list_permission_no_bearer_token(self, mock_client):
        team_permissions_response = mock_client.get(
            "/permissions",
        )
        assert team_permissions_response.status_code == 403
        assert team_permissions_response.json() == {"detail": "Not authenticated"}

    def test_list_permission_invalid_bearer_token(self, mock_client):
        invalid_token = invalidate_token(get_bearer_token_for_user(kc_config.janedoe))
        team_permissions_response = mock_client.get(
            "/permissions",
            headers=auth_header(invalid_token),
        )
        assert team_permissions_response.status_code == 401
        assert team_permissions_response.json() == {"message": "Invalid access token"}

    def test_list_permissions(self, mock_client):

        token = get_bearer_token_for_user(kc_config.janedoe)
        team_permissions_response = mock_client.get(
            "/permissions",
            params={"team_id": kc_config.team_id},
            headers=auth_header(token),
        )
        assert team_permissions_response.status_code == 200
        assert team_permissions_response.json() == [
            {
                "dataset_id": "integration-test-dataset",
                "description": "Allows for admin operations on dataset: integration-test-dataset",
                "scopes": ["okdata:dataset:admin"],
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

    def test_update_permission_forbidden(self, mock_client):
        token = get_bearer_token_for_user(kc_config.homersimpson)
        response = mock_client.put(
            f"/permissions/{dataset_id}", headers=auth_header(token)
        )
        assert response.status_code == 403
        assert response.json() == {"message": "Forbidden"}

    def test_update_permission(self, mock_client):

        assert not resource_authorizer.has_access(
            dataset_id,
            DatasetScope.read,
            get_bearer_token_for_user(kc_config.homersimpson),
        )

        token = get_bearer_token_for_user(kc_config.janedoe)

        body = {
            "add_users": [{"user_id": kc_config.homersimpson, "user_type": "user"}],
            "scope": DatasetScope.read.value,
        }
        response = mock_client.put(
            f"/permissions/{dataset_id}", json=body, headers=auth_header(token)
        )
        assert response.status_code == 200
        assert response.json() == {
            "dataset_id": "integration-test-dataset",
            "description": "Allows for read on dataset: integration-test-dataset",
            "scopes": ["okdata:dataset:read"],
            "teams": ["group1"],
            "users": [kc_config.homersimpson],
            "clients": [],
        }

        assert resource_authorizer.has_access(
            dataset_id,
            DatasetScope.read,
            get_bearer_token_for_user(kc_config.homersimpson),
        )


def get_bearer_token_for_user(username):
    token = KeycloakOpenID(
        realm_name=kc_config.realm_name,
        server_url=f"{kc_config.server_auth_url}",
        client_id=kc_config.resource_server_id,
        client_secret_key=kc_config.resource_server_secret,
    ).token(username, "password")
    return token["access_token"]


def get_token_for_service():
    client = KeycloakOpenID(
        realm_name=kc_config.realm_name,
        server_url=f"{kc_config.server_auth_url}",
        client_id=kc_config.create_permissions_client_id,
        client_secret_key=kc_config.create_permissions_client_secret,
    )
    token = client.token(grant_type=["client_credentials"])
    return token["access_token"]


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def invalidate_token(token):
    decoded = jwt.decode(token, verify=False)
    decoded["exp"] = 1610617383
    return jwt.encode(decoded, "some-key", algorithm="HS256")

from keycloak import KeycloakOpenID
from okdata.sdk.auth.util import decode_token, jwt

from dataplatform_keycloak import ResourceAuthorizer
from tests.setup import local_keycloak_config as kc_config

resource_name = "okdata:dataset:integration-test-dataset"
resource_authorizer = ResourceAuthorizer()


class TestOkdataPermissionApi:

    # POST /permissions

    def test_create_resource_forbidden(self, mock_client):
        body = {
            "owner": {
                "user_id": kc_config.team_id,
                "user_type": "team",
            },
            "resource_name": resource_name,
        }

        token = get_bearer_token_for_user(kc_config.janedoe)

        create_resource_response = mock_client.post(
            "/permissions", json=body, headers=auth_header(token)
        )
        assert create_resource_response.status_code == 403

    def test_create_resource_unknown_resource_type(self, mock_client):
        body = {
            "owner": {
                "user_id": kc_config.team_id,
                "user_type": "team",
            },
            "resource_name": "foo:bar:integration-test-dataset",
        }

        token = get_bearer_token_for_user(kc_config.janedoe)

        response = mock_client.post(
            "/permissions", json=body, headers=auth_header(token)
        )
        assert response.status_code == 400
        assert response.json()["message"] == "Bad Request"

    def test_create_resource(self, mock_client):
        body = {
            "owner": {
                "user_id": kc_config.team_id,
                "user_type": "team",
            },
            "resource_name": resource_name,
        }

        token = get_token_for_service()

        create_resource_response = mock_client.post(
            "/permissions", json=body, headers=auth_header(token)
        )
        assert create_resource_response.status_code == 201

    def test_create_resource_conflict_error(self, mock_client):
        body = {
            "owner": {
                "user_id": kc_config.team_id,
                "user_type": "team",
            },
            "resource_name": resource_name,
        }

        token = get_token_for_service()

        response = mock_client.post(
            "/permissions", json=body, headers=auth_header(token)
        )
        assert response.status_code == 409
        assert (
            response.json()["message"]
            == f"Resource with name [{resource_name}] already exists."
        )

    # GET /permissions

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
        assert team_permissions_response.json()[0] == {
            "resource_name": resource_name,
            "description": f"Allows for admin operations on resource: {resource_name}",
            "scopes": ["okdata:dataset:admin"],
            "teams": ["group1"],
            "users": [],
            "clients": [],
        }
        assert team_permissions_response.json() == [
            {
                "resource_name": resource_name,
                "description": f"Allows for admin operations on resource: {resource_name}",
                "scopes": ["okdata:dataset:admin"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "resource_name": resource_name,
                "description": f"Allows for read operations on resource: {resource_name}",
                "scopes": ["okdata:dataset:read"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "resource_name": resource_name,
                "description": f"Allows for update operations on resource: {resource_name}",
                "scopes": ["okdata:dataset:update"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "resource_name": resource_name,
                "description": f"Allows for write operations on resource: {resource_name}",
                "scopes": ["okdata:dataset:write"],
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
        ]

    # PUT /permissions/{resource_name}

    def test_update_permission_forbidden(self, mock_client):
        token = get_bearer_token_for_user(kc_config.homersimpson)
        response = mock_client.put(
            f"/permissions/{resource_name}", headers=auth_header(token)
        )
        assert response.status_code == 403
        assert response.json() == {"message": "Forbidden"}

    def test_update_permission(self, mock_client):
        assert not resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            "okdata:dataset:read",
            resource_name,
        )

        token = get_bearer_token_for_user(kc_config.janedoe)

        body = {
            "add_users": [{"user_id": kc_config.homersimpson, "user_type": "user"}],
            "scope": "okdata:dataset:read",
        }
        response = mock_client.put(
            f"/permissions/{resource_name}", json=body, headers=auth_header(token)
        )
        assert response.status_code == 200
        assert response.json() == {
            "resource_name": resource_name,
            "description": f"Allows for read operations on resource: {resource_name}",
            "scopes": ["okdata:dataset:read"],
            "teams": ["group1"],
            "users": [kc_config.homersimpson],
            "clients": [],
        }

        assert resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            "okdata:dataset:read",
            resource_name,
        )

    def test_update_permission_resource_not_exist(self, mock_client):
        token = get_bearer_token_for_user(kc_config.janedoe)
        response = mock_client.put(
            f"/permissions/{resource_name}-not-exist", headers=auth_header(token)
        )
        assert response.status_code == 400
        assert response.json() == {
            "message": f"Resource with id [{resource_name}-not-exist] does not exist."
        }


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
    decoded = decode_token(token)
    decoded["exp"] = 1610617383
    return jwt.encode(decoded, "some-key", algorithm="HS256")

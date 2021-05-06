from keycloak import KeycloakOpenID
import jwt

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

    # GET /permissions/{resource_name}

    def test_get_permissions_no_bearer_token(self, mock_client):
        response = mock_client.get(f"/permissions/{resource_name}")
        assert response.status_code == 403
        assert response.json() == {"detail": "Not authenticated"}

    def test_get_permissions_invalid_bearer_token(self, mock_client):
        invalid_token = invalidate_token(get_bearer_token_for_user(kc_config.janedoe))
        response = mock_client.get(
            f"/permissions/{resource_name}",
            headers=auth_header(invalid_token),
        )
        assert response.status_code == 401
        assert response.json() == {"message": "Invalid access token"}

    def test_get_permissions_not_admin(self, mock_client):
        token = get_bearer_token_for_user(kc_config.homersimpson)
        response = mock_client.get(
            f"/permissions/{resource_name}", headers=auth_header(token)
        )
        assert response.status_code == 403

    def test_get_permissions(self, mock_client):
        token = get_bearer_token_for_user(kc_config.janedoe)
        response = mock_client.get(
            f"/permissions/{resource_name}", headers=auth_header(token)
        )
        assert response.status_code == 200
        assert response.json() == [
            {
                "resource_name": resource_name,
                "description": f"Allows for admin operations on resource: {resource_name}",
                "scope": "okdata:dataset:admin",
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "resource_name": resource_name,
                "description": f"Allows for read operations on resource: {resource_name}",
                "scope": "okdata:dataset:read",
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "resource_name": resource_name,
                "description": f"Allows for update operations on resource: {resource_name}",
                "scope": "okdata:dataset:update",
                "teams": ["group1"],
                "users": [],
                "clients": [],
            },
            {
                "resource_name": resource_name,
                "description": f"Allows for write operations on resource: {resource_name}",
                "scope": "okdata:dataset:write",
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
            "scope": "okdata:dataset:read",
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

    def test_update_permission_create_permission_if_deleted(self, mock_client):
        token = get_bearer_token_for_user(kc_config.janedoe)

        remove_all_users_body = {
            "remove_users": [
                {"user_id": kc_config.homersimpson, "user_type": "user"},
                {"user_id": kc_config.team_id, "user_type": "team"},
            ],
            "scope": "okdata:dataset:read",
        }
        remove_all_users_response = mock_client.put(
            f"/permissions/{resource_name}",
            json=remove_all_users_body,
            headers=auth_header(token),
        )
        assert remove_all_users_response.status_code == 200
        assert remove_all_users_response.json() == {
            "resource_name": resource_name,
            "description": f"Allows for read operations on resource: {resource_name}",
            "scope": "okdata:dataset:read",
            "teams": [],
            "users": [],
            "clients": [],
        }

        assert not resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            "okdata:dataset:read",
            resource_name,
        )

        add_user_body = {
            "add_users": [{"user_id": kc_config.homersimpson, "user_type": "user"}],
            "scope": "okdata:dataset:read",
        }

        add_user_response = mock_client.put(
            f"/permissions/{resource_name}",
            json=add_user_body,
            headers=auth_header(token),
        )
        assert add_user_response.status_code == 200
        assert add_user_response.json() == {
            "resource_name": resource_name,
            "description": f"Allows for read operations on resource: {resource_name}",
            "scope": "okdata:dataset:read",
            "teams": [],
            "users": [kc_config.homersimpson],
            "clients": [],
        }

        assert resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            "okdata:dataset:read",
            resource_name,
        )

    def test_update_permissions_for_admin_scopes(self, mock_client):
        token = get_bearer_token_for_user(kc_config.janedoe)

        # Add a second admin
        mock_client.put(
            f"/permissions/{resource_name}",
            json={
                "add_users": [{"user_id": kc_config.homersimpson, "user_type": "user"}],
                "scope": "okdata:dataset:admin",
            },
            headers=auth_header(token),
        )

        assert resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            "okdata:dataset:admin",
            resource_name,
        )

        # Remove the second admin

        mock_client.put(
            f"/permissions/{resource_name}",
            json={
                "remove_users": [
                    {"user_id": kc_config.homersimpson, "user_type": "user"}
                ],
                "scope": "okdata:dataset:admin",
            },
            headers=auth_header(token),
        )

        assert not resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            "okdata:dataset:admin",
            resource_name,
        )

        # Try to remove the only remaining admin

        remove_only_admin_body = {
            "remove_users": [
                {"user_id": kc_config.team_id, "user_type": "team"},
            ],
            "scope": "okdata:dataset:admin",
        }
        remove_all_users_response = mock_client.put(
            f"/permissions/{resource_name}",
            json=remove_only_admin_body,
            headers=auth_header(token),
        )
        assert remove_all_users_response.status_code == 400
        assert remove_all_users_response.json() == {
            "message": "Cannot remove the only admin for resource"
        }

    # GET /my_permissions

    def test_get_my_permissions(self, mock_client):
        token = get_bearer_token_for_user(kc_config.homersimpson)
        response = mock_client.get("/my_permissions", headers=auth_header(token))
        assert response.status_code == 200
        response_body = response.json()
        assert set(response_body.keys()) == {resource_name}
        assert response_body[resource_name] == {"scopes": ["okdata:dataset:read"]}


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
    decoded = jwt.decode(token, options={"verify_signature": False})
    decoded["exp"] = 1610617383
    return jwt.encode(decoded, "some-key", algorithm="HS256")

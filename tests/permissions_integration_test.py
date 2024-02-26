from okdata.resource_auth import ResourceAuthorizer

from tests.setup import local_keycloak_config as kc_config
from tests.utils import (
    auth_header,
    get_bearer_token_for_user,
    get_token_for_service,
    invalidate_token,
)

resource_name = "okdata:dataset:integration-test-dataset"
resource_authorizer = ResourceAuthorizer()


###############################################################################
# POST /permissions
###############################################################################


def test_create_resource_forbidden(mock_client):
    body = {
        "owner": {"user_id": kc_config.team1, "user_type": "team"},
        "resource_name": resource_name,
    }
    token = get_bearer_token_for_user(kc_config.janedoe)

    create_resource_response = mock_client.post(
        "/permissions", json=body, headers=auth_header(token)
    )
    assert create_resource_response.status_code == 403


def test_create_resource_unknown_resource_type(mock_client):
    body = {
        "owner": {"user_id": kc_config.team1, "user_type": "team"},
        "resource_name": "foo:bar:integration-test-dataset",
    }
    token = get_token_for_service(
        kc_config.create_permissions_client_id,
        kc_config.create_permissions_client_secret,
    )

    response = mock_client.post(
        "/permissions",
        json=body,
        headers=auth_header(token),
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Bad Request"


def test_create_resource(mock_client):
    body = {
        "owner": {"user_id": kc_config.team1, "user_type": "team"},
        "resource_name": resource_name,
    }
    token = get_token_for_service(
        kc_config.create_permissions_client_id,
        kc_config.create_permissions_client_secret,
    )

    create_resource_response = mock_client.post(
        "/permissions", json=body, headers=auth_header(token)
    )
    assert create_resource_response.status_code == 201


def test_create_resource_conflict_error(mock_client):
    body = {
        "owner": {"user_id": kc_config.team1, "user_type": "team"},
        "resource_name": resource_name,
    }
    token = get_token_for_service(
        kc_config.create_permissions_client_id,
        kc_config.create_permissions_client_secret,
    )

    response = mock_client.post(
        "/permissions",
        json=body,
        headers=auth_header(token),
    )
    assert response.status_code == 409
    assert (
        response.json()["message"]
        == f"Resource with name [{resource_name}] already exists."
    )


###############################################################################
# GET /permissions/{resource_name}
###############################################################################


def test_get_permissions_no_bearer_token(mock_client):
    response = mock_client.get(f"/permissions/{resource_name}")
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_get_permissions_invalid_bearer_token(mock_client):
    invalid_token = invalidate_token(
        get_bearer_token_for_user(kc_config.janedoe),
    )
    response = mock_client.get(
        f"/permissions/{resource_name}", headers=auth_header(invalid_token)
    )
    assert response.status_code == 401
    assert response.json() == {"message": "Invalid access token"}


def test_get_permissions_not_admin(mock_client):
    token = get_bearer_token_for_user(kc_config.homersimpson)
    response = mock_client.get(
        f"/permissions/{resource_name}", headers=auth_header(token)
    )
    assert response.status_code == 403


def test_get_permissions(mock_client):
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
            "teams": ["team1"],
            "users": [],
            "clients": [],
        },
        {
            "resource_name": resource_name,
            "description": f"Allows for read operations on resource: {resource_name}",
            "scope": "okdata:dataset:read",
            "teams": ["team1"],
            "users": [],
            "clients": [],
        },
        {
            "resource_name": resource_name,
            "description": f"Allows for update operations on resource: {resource_name}",
            "scope": "okdata:dataset:update",
            "teams": ["team1"],
            "users": [],
            "clients": [],
        },
        {
            "resource_name": resource_name,
            "description": f"Allows for write operations on resource: {resource_name}",
            "scope": "okdata:dataset:write",
            "teams": ["team1"],
            "users": [],
            "clients": [],
        },
    ]


def test_get_permissions_resource_not_found(mock_client):
    token = get_token_for_service(
        kc_config.create_permissions_client_id,
        kc_config.create_permissions_client_secret,
    )
    response = mock_client.get(
        "/permissions/okdata:dataset:nil", headers=auth_header(token)
    )
    assert response.status_code == 404
    assert response.json() == {
        "message": "No resource named okdata:dataset:nil",
    }


###############################################################################
# PUT /permissions/{resource_name}
###############################################################################


def test_update_permission_forbidden(mock_client):
    token = get_bearer_token_for_user(kc_config.homersimpson)
    response = mock_client.put(
        f"/permissions/{resource_name}", headers=auth_header(token)
    )
    assert response.status_code == 403
    assert response.json() == {"message": "Forbidden"}


def test_update_permission(mock_client):
    assert not resource_authorizer.has_access(
        get_bearer_token_for_user(kc_config.homersimpson),
        "okdata:dataset:read",
        resource_name,
    )

    token = get_bearer_token_for_user(kc_config.janedoe)

    body = {
        "add_users": [
            {"user_id": kc_config.homersimpson, "user_type": "user"},
        ],
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
        "teams": ["team1"],
        "users": [kc_config.homersimpson],
        "clients": [],
    }

    assert resource_authorizer.has_access(
        get_bearer_token_for_user(kc_config.homersimpson),
        "okdata:dataset:read",
        resource_name,
    )


def test_update_permission_all(mock_client):
    for permission in ["admin", "update", "write"]:
        assert not resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            f"okdata:dataset:{permission}",
            resource_name,
        )

    res = mock_client.put(
        f"/permissions/{resource_name}",
        json={
            "add_users": [{"user_id": kc_config.homersimpson, "user_type": "user"}],
            "scope": "__all__",
        },
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert res.status_code == 200

    for permission in ["admin", "update", "write"]:
        assert resource_authorizer.has_access(
            get_bearer_token_for_user(kc_config.homersimpson),
            f"okdata:dataset:{permission}",
            resource_name,
        )


def test_update_permission_team(mock_client):
    assert not resource_authorizer.has_access(
        get_bearer_token_for_user(kc_config.team2member),
        "okdata:dataset:read",
        resource_name,
    )

    token = get_bearer_token_for_user(kc_config.janedoe)
    body = {
        "add_users": [{"user_id": kc_config.team2, "user_type": "team"}],
        "scope": "okdata:dataset:read",
    }

    response = mock_client.put(
        f"/permissions/{resource_name}", json=body, headers=auth_header(token)
    )
    assert response.status_code == 200
    assert set(response.json()["teams"]) == {"team1", "team2"}

    assert resource_authorizer.has_access(
        get_bearer_token_for_user(kc_config.team2member),
        "okdata:dataset:read",
        resource_name,
    )


def test_update_permission_unknown_scope(mock_client):
    response = mock_client.put(
        f"/permissions/{resource_name}",
        json={
            "add_users": [
                {"user_id": kc_config.homersimpson, "user_type": "user"},
            ],
            "scope": "okdata:dataset:foobar",
        },
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 400
    assert (
        "Some of the scopes [[okdata:dataset:foobar]] are not valid for resource"
        in response.json()["message"]
    )


def test_update_permission_resource_not_exist(mock_client):
    token = get_bearer_token_for_user(kc_config.janedoe)
    response = mock_client.put(
        f"/permissions/{resource_name}-not-exist", headers=auth_header(token)
    )
    assert response.status_code == 403
    assert response.json() == {"message": "Forbidden"}


def test_update_permission_create_permission_if_deleted(mock_client):
    token = get_bearer_token_for_user(kc_config.janedoe)

    remove_all_users_body = {
        "remove_users": [
            {"user_id": kc_config.homersimpson, "user_type": "user"},
            {"user_id": kc_config.team1, "user_type": "team"},
            {"user_id": kc_config.team2, "user_type": "team"},
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
        "add_users": [
            {"user_id": kc_config.homersimpson, "user_type": "user"},
        ],
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


def test_update_permissions_for_admin_scopes(mock_client):
    token = get_bearer_token_for_user(kc_config.janedoe)

    # Add a second admin
    mock_client.put(
        f"/permissions/{resource_name}",
        json={
            "add_users": [
                {"user_id": kc_config.homersimpson, "user_type": "user"},
            ],
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
                {"user_id": kc_config.homersimpson, "user_type": "user"},
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
            {"user_id": kc_config.team1, "user_type": "team"},
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


###############################################################################
# GET /my_permissions
###############################################################################


def test_get_my_permissions(mock_client):
    token = get_bearer_token_for_user(kc_config.homersimpson)
    response = mock_client.get("/my_permissions", headers=auth_header(token))
    assert response.status_code == 200
    response_body = response.json()
    assert set(response_body.keys()) == {resource_name}
    assert set(response_body[resource_name]["scopes"]) == {
        "okdata:dataset:read",
        "okdata:dataset:update",
        "okdata:dataset:write",
    }


def test_get_my_permissions_filtered(mock_client):
    token = get_bearer_token_for_user(kc_config.homersimpson)

    # Add another resource of different type
    mock_client.post(
        "/permissions",
        json={
            "owner": {"user_id": kc_config.homersimpson, "user_type": "user"},
            "resource_name": "maskinporten:client:test-client",
        },
        headers=auth_header(
            get_token_for_service(
                kc_config.create_permissions_client_id,
                kc_config.create_permissions_client_secret,
            )
        ),
    )

    def get_resources(resource_type_filter=None):
        response = mock_client.get(
            "/my_permissions",
            headers=auth_header(token),
            params={"resource_type": resource_type_filter},
        )
        assert response.status_code == 200
        return set(response.json().keys())

    assert get_resources("okdata:dataset") == {resource_name}
    assert get_resources("maskinporten:client") == {
        "maskinporten:client:test-client",
    }
    assert len(get_resources("foo:bar")) == 0
    assert len(get_resources()) == 2


def test_get_my_permissions_no_permissions(mock_client):
    token = get_bearer_token_for_user(kc_config.nopermissions)
    response = mock_client.get("/my_permissions", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == {}


###############################################################################
# DELETE /permissions/{resource_name}
###############################################################################


def test_delete_resource_no_bearer_token(mock_client):
    response = mock_client.delete(f"/permissions/{resource_name}")
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_delete_resource_invalid_bearer_token(mock_client):
    invalid_token = invalidate_token(
        get_bearer_token_for_user(kc_config.janedoe),
    )
    response = mock_client.delete(
        f"/permissions/{resource_name}", headers=auth_header(invalid_token)
    )
    assert response.status_code == 401
    assert response.json() == {"message": "Invalid access token"}


def test_delete_resource_not_admin(mock_client):
    token = get_bearer_token_for_user(kc_config.janedoe)
    response = mock_client.delete(
        f"/permissions/{resource_name}", headers=auth_header(token)
    )
    assert response.status_code == 403


def test_delete_resource_success(mock_client):
    user_token = get_bearer_token_for_user(kc_config.janedoe)
    service_token = get_token_for_service(
        kc_config.create_permissions_client_id,
        kc_config.create_permissions_client_secret,
    )

    get_response_before = mock_client.get(
        f"/permissions/{resource_name}", headers=auth_header(user_token)
    )
    assert get_response_before.status_code == 200

    delete_response = mock_client.delete(
        f"/permissions/{resource_name}", headers=auth_header(service_token)
    )
    assert delete_response.status_code == 200

    get_response_after = mock_client.get(
        f"/permissions/{resource_name}", headers=auth_header(user_token)
    )
    assert get_response_after.status_code == 403

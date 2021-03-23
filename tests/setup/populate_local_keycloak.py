import time
import json
from datetime import datetime, timedelta
from keycloak import KeycloakAdmin, KeycloakGetError
from keycloak.exceptions import KeycloakConnectionError
import tests.setup.local_keycloak_config as keycloak_config


def populate():

    keycloak_admin = initialize_keycloak_admin()

    # Clear data from previous test runs
    try:
        keycloak_admin.delete_realm(keycloak_config.realm_name)
    except KeycloakGetError:
        pass

    # Create new realm
    keycloak_admin.create_realm(
        payload={
            "enabled": True,
            "id": keycloak_config.realm_name,
            "realm": keycloak_config.realm_name,
            "userManagedAccessAllowed": True,
        },
        skip_exists=True,
    )

    # Use new realm
    keycloak_admin.realm_name = keycloak_config.realm_name

    # Create resource server
    keycloak_admin.create_client(
        payload={
            "id": keycloak_config.resource_server_id,
            "name": keycloak_config.resource_server_id,
            "redirectUris": ["*"],
            "publicClient": False,
            "authorizationServicesEnabled": True,
            "serviceAccountsEnabled": True,
            "directAccessGrantsEnabled": True,
            "secret": keycloak_config.resource_server_secret,
        },
        skip_exists=True,
    )

    # Create client for this service (okdata-permission-api)
    keycloak_admin.create_client(
        payload={
            "id": keycloak_config.client_id,
            "name": keycloak_config.client_id,
            "publicClient": False,
            "serviceAccountsEnabled": True,
            "secret": keycloak_config.client_secret,
        },
        skip_exists=True,
    )

    # Create client that simulates another service
    keycloak_admin.create_client(
        payload={
            "id": keycloak_config.create_permissions_client_id,
            "name": keycloak_config.create_permissions_client_id,
            "publicClient": False,
            "serviceAccountsEnabled": True,
            "secret": keycloak_config.create_permissions_client_secret,
        },
        skip_exists=True,
    )

    #  Create scope, policy and permission allowing another service to create resources

    create_resource_scope_body = {
        "name": "createResource",
        "displayName": "createResource",
    }
    create_resource_scope = keycloak_admin.raw_post(
        path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/scope",
        data=json.dumps(create_resource_scope_body),
    ).json()

    create_resource_policy_body = {
        "type": "client",
        "logic": "POSITIVE",
        "decisionStrategy": "AFFIRMATIVE",
        "name": "createResource",
        "description": "Clients that can create resources",
        "clients": [keycloak_config.create_permissions_client_id],
    }
    create_resource_policy = keycloak_admin.raw_post(
        path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/policy/client",
        data=json.dumps(create_resource_policy_body),
    ).json()

    create_resource_permission_body = {
        "type": "scope",
        "logic": "POSITIVE",
        "decisionStrategy": "UNANIMOUS",
        "name": "createResourcePermission",
        "description": "Allows for creating resources",
        "scopes": [create_resource_scope["id"]],
        "policies": [create_resource_policy["id"]],
    }
    keycloak_admin.raw_post(
        path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/permission/scope",
        data=json.dumps(create_resource_permission_body),
    )

    # Create users and groups
    for user in keycloak_config.users:
        for group in user["groups"]:
            keycloak_admin.create_group(payload={"name": group}, skip_exists=True)
        keycloak_admin.create_user(
            payload={
                "username": user["username"],
                "groups": user["groups"],
                "enabled": True,
                "credentials": [
                    {"type": "password", "value": "password", "temporary": False}
                ],
            }
        )


def initialize_keycloak_admin(timeout_seconds=30.0):
    start = datetime.now()
    while datetime.now() < start + timedelta(0, timeout_seconds):
        try:
            print("Trying to connect to local keycloak")
            keycloak_admin = KeycloakAdmin(
                server_url=keycloak_config.server_url,
                username="admin",
                password="admin",
                realm_name="master",
                verify=True,
            )
            print(f"Connected after {(datetime.now() - start).seconds} seconds")
            return keycloak_admin
        except KeycloakConnectionError:
            pass

        time.sleep(1)


if __name__ == "__main__":
    populate()

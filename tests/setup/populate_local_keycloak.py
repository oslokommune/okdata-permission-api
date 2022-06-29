import json
import time
from datetime import datetime, timedelta
from typing import List

from keycloak import KeycloakAdmin, KeycloakDeleteError
from keycloak.exceptions import KeycloakConnectionError

from dataplatform_keycloak.groups import group_name_to_team_name
import tests.setup.local_keycloak_config as keycloak_config


def populate():

    keycloak_admin = initialize_keycloak_admin()

    # Clear data from previous test runs
    try:
        keycloak_admin.delete_realm(keycloak_config.realm_name)
    except KeycloakDeleteError:
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
    # Delete default resource
    for resource in keycloak_admin.raw_get(
        path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/resource"
    ).json():
        resource_id = resource["_id"]
        keycloak_admin.raw_delete(
            path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/resource/{resource_id}"
        )

    # helper method for creating a client that can represent a service in integration tests
    def create_service_client(client_id, client_secret):
        keycloak_admin.create_client(
            payload={
                "id": client_id,
                "name": client_id,
                "publicClient": False,
                "serviceAccountsEnabled": True,
                "secret": client_secret,
            },
            skip_exists=True,
        )

    # helper method for creating a scope and associated policy and permission
    def create_scope_permission(
        scope: str,
        clients: List[str],
        policy_name: str,
        permission_name: str,
    ):

        create_scope_body = {
            "name": scope,
            "displayName": scope,
        }
        created_scope = keycloak_admin.raw_post(
            path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/scope",
            data=json.dumps(create_scope_body),
        ).json()

        create_policy_body = {
            "type": "client",
            "logic": "POSITIVE",
            "decisionStrategy": "AFFIRMATIVE",
            "name": policy_name,
            "clients": clients,
        }
        policy = keycloak_admin.raw_post(
            path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/policy/client",
            data=json.dumps(create_policy_body),
        ).json()

        create_permission_body = {
            "type": "scope",
            "logic": "POSITIVE",
            "decisionStrategy": "UNANIMOUS",
            "name": permission_name,
            "description": f"Permission that grants access to {scope} scope",
            "scopes": [created_scope["id"]],
            "policies": [policy["id"]],
        }
        keycloak_admin.raw_post(
            path=f"admin/realms/{keycloak_config.realm_name}/clients/{keycloak_config.resource_server_id}/authz/resource-server/permission/scope",
            data=json.dumps(create_permission_body),
        )

    # Create service client for this service (okdata-permission-api)
    create_service_client(keycloak_config.client_id, keycloak_config.client_secret)

    # Create service client simulating another service that will have permission to create resources
    create_service_client(
        keycloak_config.create_permissions_client_id,
        keycloak_config.create_permissions_client_secret,
    )

    # Create scope, policy and permission allowing another service to administrate
    # Keycloak resources, e.g. `okdata-metadata-api`.
    create_scope_permission(
        scope="keycloak:resource:admin",
        clients=[keycloak_config.create_permissions_client_id],
        policy_name="keycloak_resource_admin_policy",
        permission_name="keycloak_resource_admin_permission",
    )

    # Create service client simulating another service that will have permission to remove any team from all permissions
    create_service_client(
        keycloak_config.remove_team_client_id, keycloak_config.remove_team_client_secret
    )

    # Create scope, policy and permission allowing another service to a team from all permissions
    create_scope_permission(
        scope="okdata:team:admin",
        clients=[keycloak_config.remove_team_client_id],
        policy_name="remove_team_permissions_policy",
        permission_name="remove_team_permissions_permission",
    )

    # Create team admin user
    team_admin_user_id = keycloak_admin.create_user(
        payload={
            "username": keycloak_config.team_admin_username,
            "enabled": True,
            "credentials": [
                {
                    "type": "password",
                    "value": keycloak_config.team_admin_password,
                    "temporary": False,
                }
            ],
        }
    )

    realm_management_client_id = keycloak_admin.get_client_id("realm-management")

    client_roles = [
        keycloak_admin.get_client_role(
            client_id=realm_management_client_id,
            role_name=role_name,
        )
        for role_name in keycloak_config.team_admin_client_roles
    ]

    keycloak_admin.assign_client_role(
        user_id=team_admin_user_id,
        client_id=realm_management_client_id,
        roles=client_roles,
    )

    # Create groups
    for group in keycloak_config.groups:
        keycloak_admin.create_group(payload=group)

    # Create users and groups
    for user in keycloak_config.users:
        keycloak_admin.create_user(
            payload={
                "username": user["username"],
                "groups": user["groups"],
                "enabled": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": "password",
                        "temporary": False,
                    },
                ],
            }
        )

    keycloak_admin.create_realm_role(
        payload={
            "name": keycloak_config.internal_team_realm_role,
        },
        skip_exists=True,
    )
    internal_team_realm_role = keycloak_admin.get_realm_role(
        keycloak_config.internal_team_realm_role
    )
    for group in keycloak_admin.get_groups():
        group_name = group_name_to_team_name(group["name"])
        if group_name in keycloak_config.internal_teams:
            keycloak_admin.assign_group_realm_roles(
                group["id"], internal_team_realm_role
            )


# Method for test that will ensure that this bug does not occur: https://confluence.oslo.kommune.no/pages/viewpage.action?pageId=162566147
def delete_team(team_name: str):
    keycloak_admin = initialize_keycloak_admin()
    get_groups_response = keycloak_admin.raw_get(
        f"admin/realms/{keycloak_config.realm_name}/groups"
    )
    get_groups_response.raise_for_status()

    for group in get_groups_response.json():
        if group["name"] == f"TEAM-{team_name}":
            delete_response = keycloak_admin.raw_delete(
                f"admin/realms/{keycloak_config.realm_name}/groups/{group['id']}"
            )
            delete_response.raise_for_status()


def initialize_keycloak_admin(timeout_seconds=30.0):
    start = datetime.now()
    while datetime.now() < start + timedelta(0, timeout_seconds):
        try:
            print("Trying to connect to local keycloak")
            keycloak_admin = KeycloakAdmin(
                server_url=keycloak_config.server_auth_url,
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
    return None


if __name__ == "__main__":
    populate()

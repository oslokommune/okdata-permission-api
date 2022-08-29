import jwt
from keycloak import KeycloakOpenID

from dataplatform_keycloak.teams_client import TeamsClient
import tests.setup.local_keycloak_config as kc_config


def get_bearer_token_for_user(username):
    token = KeycloakOpenID(
        realm_name=kc_config.realm_name,
        server_url=f"{kc_config.server_auth_url}",
        client_id=kc_config.resource_server_id,
        client_secret_key=kc_config.resource_server_secret,
    ).token(username, "password")
    return token["access_token"]


def get_token_for_service(service_client_id, service_client_secret):
    client = KeycloakOpenID(
        realm_name=kc_config.realm_name,
        server_url=f"{kc_config.server_auth_url}",
        client_id=service_client_id,
        client_secret_key=service_client_secret,
    )
    token = client.token(grant_type=["client_credentials"])
    return token["access_token"]


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def invalidate_token(token):
    decoded = jwt.decode(token, options={"verify_signature": False})
    decoded["exp"] = 1610617383
    return jwt.encode(decoded, "some-key", algorithm="HS256")


def get_keycloak_group_by_name(group_name):
    for group in TeamsClient().teams_admin_client.get_groups():
        if group["name"] == group_name:
            return group
    return None


def get_keycloak_user_id_by_username(username):
    teams_client = TeamsClient().teams_admin_client
    return teams_client.get_user_id(username)


def set_keycloak_group_members(group_id, usernames):
    teams_client = TeamsClient().teams_admin_client
    for user in teams_client.get_group_members(group_id):
        teams_client.group_user_remove(user["id"], group_id)
    for username in usernames:
        teams_client.group_user_add(
            get_keycloak_user_id_by_username(username), group_id
        )

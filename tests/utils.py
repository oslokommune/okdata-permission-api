import jwt
from keycloak import KeycloakOpenID

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

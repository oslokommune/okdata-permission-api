import os
from pprint import PrettyPrinter

# import requests
from dataplatform_keycloak import ResourceServer
from tests.setup import local_keycloak_config as kc_config
from models import User

# Python script for playing around with the api running on localhost

pp = PrettyPrinter(indent=2)


def initialize_local_environment():
    os.environ["KEYCLOAK_REALM"] = kc_config.realm_name
    os.environ["KEYCLOAK_SERVER"] = kc_config.server_url
    os.environ["CLIENT_ID"] = kc_config.client_id
    os.environ["CLIENT_SECRET"] = kc_config.client_secret
    os.environ["RESOURCE_SERVER_CLIENT_ID"] = kc_config.resource_server_id
    os.environ["RESOURCE_SERVER_CLIENT_SECRET"] = kc_config.resource_server_secret


if __name__ == "__main__":
    initialize_local_environment()
    from tests.integration_test import get_token_for_service

    rm = ResourceServer()

    janedoe_user = User.parse_obj({"user_id": "janedoe", "user_type": "user"})
    janedoe_access_token = rm.resource_server_client.token("janedoe", "password")[
        "access_token"
    ]
    homersimpson_access_token = rm.resource_server_client.token(
        "homersimpson", "password"
    )["access_token"]
    resource_server_access_token = rm.resource_server_client.token(
        grant_type=["client_credentials"]
    )

    create_resource_client = User.parse_obj(
        {"user_id": kc_config.create_permissions_client_id, "user_type": "client"}
    )
    create_resource_client_access_token = get_token_for_service()

    base_url = "http://127.0.0.1:8000"

    print("Jane Doe token:")
    print(janedoe_access_token)
    print("Homer Simpson token:")
    print(homersimpson_access_token)
    print("Client that can create permissions access token")
    print(create_resource_client_access_token)

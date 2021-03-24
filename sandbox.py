import os
from dataplatform_keycloak import ResourceServer
from pprint import PrettyPrinter
from tests.setup import local_keycloak_config as kc_config

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

    rm = ResourceServer()

    janedoe_access_token = rm.resource_server_client.token("janedoe", "password")[
        "access_token"
    ]
    homersimpson_access_token = rm.resource_server_client.token(
        "homersimpson", "password"
    )["access_token"]
    resource_server_access_token = rm.resource_server_client.token(
        grant_type=["client_credentials"]
    )

    print("Jane Doe token:")
    print(janedoe_access_token)
    print("Homer Simpson token:")
    print(homersimpson_access_token)

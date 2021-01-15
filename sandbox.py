from keycloak import KeycloakOpenID

from dataplatform_keycloak import ResourceServer
from pprint import PrettyPrinter
from tests.setup import local_keycloak_config as kc_config

pp = PrettyPrinter(indent=2)

if __name__ == "__main__":
    rm = ResourceServer()

    pp.pprint(rm.resource_server_client.token("janedoe", "password"))

    client = KeycloakOpenID(
        realm_name=kc_config.realm_name,
        server_url=f"{kc_config.server_url}",
        client_id=kc_config.create_resource_client_id,
        client_secret_key=kc_config.create_resource_client_secret,
    )
    # token = client.token(grant_type=["client_credentials"])
    # print(token["access_token"])

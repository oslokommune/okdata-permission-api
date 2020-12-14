import time
from datetime import datetime, timedelta
from keycloak import KeycloakAdmin, KeycloakGetError
from keycloak.exceptions import KeycloakConnectionError


def populate(realm_name, resource_server_id, users):

    keycloak_admin = initialize_keycloak_admin()

    try:
        keycloak_admin.delete_realm(realm_name)
    except KeycloakGetError:
        pass

    keycloak_admin.create_realm(
        payload={
            "enabled": True,
            "id": realm_name,
            "realm": realm_name,
            "userManagedAccessAllowed": True,
        },
        skip_exists=True,
    )

    keycloak_admin.realm_name = realm_name

    keycloak_admin.create_client(
        payload={
            "id": resource_server_id,
            "name": resource_server_id,
            "redirectUris": ["*"],
            "publicClient": False,
            "authorizationServicesEnabled": True,
            "serviceAccountsEnabled": True,
            "directAccessGrantsEnabled": True,
            "secret": "8acda364-eafa-4a03-8fa6-b019a48ddafe",
        },
        skip_exists=True,
    )

    for user in users:
        for group in user["groups"]:
            keycloak_admin.create_group(payload={"name": group}, skip_exists=True)
        keycloak_admin.create_user(
            payload={
                "username": user["username"],
                "groups": user["groups"],
                "enabled": True,
                "credentials": [
                    {"type": "password", "value": "passord", "temporary": False}
                ],
            }
        )


def initialize_keycloak_admin(timeout_seconds=30.0):
    start = datetime.now()
    while datetime.now() < start + timedelta(0, timeout_seconds):
        try:
            print("Trying to connect to local keycloak")
            keycloak_admin = KeycloakAdmin(
                server_url="http://localhost:35789/auth/",
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
    populate(
        realm_name="dataplatform",
        resource_server_id="resource_server",
        users=[
            {"username": "janedoe", "groups": ["group1"]},
            {"username": "homersimpson", "groups": []},
        ],
    )

import os

from dataplatform_keycloak.teams_client import TeamsClient


def test_teams_client_no_connection_proxy():
    teams_client = TeamsClient()
    admin_client = teams_client.teams_admin_client
    assert admin_client.server_url == admin_client.connection.base_url


def test_teams_client_with_connection_proxy(monkeypatch):
    jwt = "foobar"
    keycloak_proxy_url = "http://kc.mock-kong.com"

    monkeypatch.setattr("dataplatform_keycloak.teams_client.generate_jwt", lambda: jwt)

    teams_client = TeamsClient(keycloak_admin_api_url=keycloak_proxy_url)
    admin_client = teams_client.teams_admin_client

    assert admin_client.server_url == os.environ["KEYCLOAK_SERVER"] + "/auth/"
    assert admin_client.connection.base_url == keycloak_proxy_url
    assert admin_client.connection.headers["Authorization"] == f"Bearer {jwt}"
    assert (
        admin_client.connection.headers["Keycloak-Authorization"]
        == f"Bearer {admin_client.token['access_token']}"
    )

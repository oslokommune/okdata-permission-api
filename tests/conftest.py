import pytest
from fastapi.testclient import TestClient

import tests.setup.local_keycloak_config as kc_config
from app import app
from dataplatform_keycloak.ssm import SsmClient


@pytest.fixture
def mock_client(mock_ssm_client):
    app.debug = True
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_ssm_client(monkeypatch):
    def get_secret(key):
        if (
            key
            == f"/dataplatform/{kc_config.resource_server_id}/keycloak-client-secret"
        ):
            return kc_config.resource_server_secret
        elif key == f"/dataplatform/{kc_config.client_id}/keycloak-client-secret":
            return kc_config.client_secret
        elif key == "/dataplatform/teams-api/keycloak-teams-admin-password":
            return kc_config.team_admin_password
        elif key == "/dataplatform/teams-api/kong-keycloak-jwt-issuer":
            return "jwt-issuer"
        elif key == "/dataplatform/teams-api/kong-keycloak-jwt-secret":
            return "jwt-secret"
        return None

    monkeypatch.setattr(SsmClient, "get_secret", get_secret)

import pytest
from fastapi.testclient import TestClient
import tests.setup.local_keycloak_config as kc_config
from dataplatform_keycloak.ssm import SsmClient
from app import app


@pytest.fixture
def mock_client(mock_ssm_client):
    app.debug = True
    return TestClient(app)


@pytest.fixture
def mock_ssm_client(monkeypatch):
    def get_secret(key):
        if key == f"/dataplatform/{kc_config.resource_server_id}/client_secret":
            return kc_config.resource_server_secret
        elif key == f"/dataplatform/{kc_config.client_id}/client_secret":
            return kc_config.client_secret

    monkeypatch.setattr(SsmClient, "get_secret", get_secret)

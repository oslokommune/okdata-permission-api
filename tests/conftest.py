import pytest
from fastapi.testclient import TestClient
import tests.setup.local_keycloak_config as local_keycloak_config
from dataplatform_keycloak.ssm import SsmClient
from app import app


@pytest.fixture
def mock_client(mock_ssm_client):
    app.debug = True
    return TestClient(app)


@pytest.fixture
def mock_ssm_client(monkeypatch):
    def get_secret(key):
        return local_keycloak_config.resource_server_secret

    monkeypatch.setattr(SsmClient, "get_secret", get_secret)

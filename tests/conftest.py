import pytest
import tests.setup.local_keycloak_config as local_keycloak_config
from dataplatform_keycloak.ssm import SsmClient


@pytest.fixture
def mock_ssm_client(monkeypatch):
    def get_secret(self, key):
        return local_keycloak_config.resource_server_secret

    monkeypatch.setattr(SsmClient, "get_secret", get_secret)

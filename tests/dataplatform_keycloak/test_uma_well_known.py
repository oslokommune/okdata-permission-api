import pytest

from dataplatform_keycloak.uma_well_known import _validate, WellKnownConfigException


def test_validate():
    assert _validate("https://example.org", "https://example.org")
    assert _validate("https://example.org/token-endpoint", "https://example.org")

    with pytest.raises(WellKnownConfigException):
        _validate("https://malicious.org/token-endpoint", "https://example.org")

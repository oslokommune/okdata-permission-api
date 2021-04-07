from unittest.mock import patch

import pytest

from models import OkdataPermission


@pytest.fixture
def uma_permission():
    return {
        "name": "okdata:dataset:foo:read",
        "description": "Allows reading the dataset `foo`.",
        "scopes": ["okdata:dataset:read"],
        "groups": [],
        "users": ["user"],
        "clients": [],
        "logic": "POSITIVE",
        "decisionStrategy": "AFFIRMATIVE",
    }


@patch("models.scope._SCOPES", {"okdata:dataset": ["read"]})
def test_okdata_permission_from_uma_permission(uma_permission):
    p = OkdataPermission.from_uma_permission(uma_permission)
    assert p.resource_name == "okdata:dataset:foo"
    assert p.description == "Allows reading the dataset `foo`."
    assert p.scopes == ["okdata:dataset:read"]
    assert p.teams == []
    assert p.users == ["user"]
    assert p.clients == []


@patch("models.scope._SCOPES", {"okdata:dataset": ["write"]})
def test_okdata_permission_from_uma_permission_unkown_scope(uma_permission):
    with pytest.raises(ValueError):
        OkdataPermission.from_uma_permission(uma_permission)

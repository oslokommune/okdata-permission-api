from unittest.mock import patch

import pytest

from models.scope import all_scopes, all_scopes_for_type, scope_permission


_SCOPES = {
    "okdata:foo": ["p1", "p2"],
    "okdata:bar": ["p3"],
}


@patch("models.scope._SCOPES", _SCOPES)
def test_all_scopes():
    assert all_scopes() == ["okdata:foo:p1", "okdata:foo:p2", "okdata:bar:p3"]


@patch("models.scope._SCOPES", _SCOPES)
def test_all_scopes_for_type():
    assert all_scopes_for_type("okdata:foo") == ["okdata:foo:p1", "okdata:foo:p2"]
    assert all_scopes_for_type("okdata:bar") == ["okdata:bar:p3"]
    with pytest.raises(ValueError):
        all_scopes_for_type("okdata:baz")


def test_scope_permission():
    assert scope_permission("namespace:type:permission") == "permission"

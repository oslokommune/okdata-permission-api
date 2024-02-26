"""Definitions of known scopes and utilities for handling them."""

_SCOPES = {
    "okdata:dataset": [
        "read",
        "write",
        "update",
        "admin",
    ],
    "maskinporten:client": [
        "read",
        "write",
    ],
}


def all_scopes():
    """Return a list of every scope defined in `_SCOPES`."""
    scopes = []
    for resource_type, permissions in _SCOPES.items():
        for permission in permissions:
            scopes.append(f"{resource_type}:{permission}")
    return scopes


def all_scopes_for_type(resource_type):
    """Return every defined scope for `resource_type`.

    Scopes are defined in `_SCOPES`.
    """
    if resource_type not in _SCOPES:
        raise ValueError(
            "Unknown resource type: {}. Must be one of: {}".format(
                resource_type, list(_SCOPES.keys())
            )
        )
    return [f"{resource_type}:{permission}" for permission in _SCOPES[resource_type]]


def resource_type(resource_name):
    """Return the namespaced resource type of `resource_name`.

    I.e. "namespace:type" from "namespace:type:name".
    """
    return ":".join(resource_name.split(":")[:2])


def scope_permission(scope):
    """Return the permission part of `scope`.

    I.e. "permission" from "namespace:type:permission".
    """
    return scope.split(":")[-1]

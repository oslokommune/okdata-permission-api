"""Utilities for resource handling."""


def resource_type(resource_name):
    """Return the (namespaced) type part of `resource_name`.

    I.e. "namespace:type" from "namespace:type:id".
    """
    return ":".join(resource_name.split(":")[:2])


def resource_id(resource_name):
    """Return the ID part of `resource_name`.

    I.e. "id" from "namespace:type:id".
    """
    return resource_name.split(":")[-1]


def resource_name_from_permission_name(permission_name):
    """Return the (namespaced) resource name part of `permission_name`.

    I.e. "namespace:type:id" form "namespace:type:id:scope".
    """
    return ":".join(permission_name.split(":")[:3])

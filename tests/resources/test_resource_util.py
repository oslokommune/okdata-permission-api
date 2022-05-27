from resources.resource_util import (
    resource_id_from_resource_name,
    resource_type_from_resource_name,
)


def test_resource_type_from_resource_name():
    assert resource_type_from_resource_name("namespace:type:id") == "namespace:type"


def test_resource_id_from_resource_name():
    assert resource_id_from_resource_name("namespace:type:id") == "id"

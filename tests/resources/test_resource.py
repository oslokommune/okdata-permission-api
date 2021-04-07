from resources.resource import resource_id, resource_type


def test_resource_type():
    assert resource_type("namespace:type:id") == "namespace:type"


def test_resource_id():
    assert resource_id("namespace:type:id") == "id"

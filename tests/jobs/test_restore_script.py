import unittest

from dataplatform_keycloak.resource_server import ResourceServer
from models import User, UserType
from scripts.restore_permissions_backup import restore_permissions
from tests.setup import populate_local_keycloak


janedoe_user = User(user_id="janedoe", user_type=UserType.USER)
homersimpson_user = User(user_id="homersimpson", user_type=UserType.USER)
someservice_client = User(user_id="some-service", user_type=UserType.CLIENT)


def uma_permission(resource_id, scope, users, resource_type="dataset"):
    permission = {
        "id": "abc-123",
        "name": f"okdata:{resource_type}:{resource_id}:{scope}",
        "description": f"Allows for {scope} operations on resource: okdata:{resource_type}:{resource_id}",
        "type": "uma",
        "scopes": [f"okdata:{resource_type}:{scope}"],
        "logic": "POSITIVE",
        "decisionStrategy": "AFFIRMATIVE",
        "owner": "okdata-resource-server",
    }
    for user in users:
        if user.user_type == UserType.USER:
            permission.setdefault("users", []).append(user.user_id)
        if user.user_type == UserType.GROUP:
            permission.setdefault("groups", []).append(user.user_id)
        if user.user_type == UserType.CLIENT:
            permission.setdefault("clients", []).append(user.user_id)
    return permission


class TestPermissionsBackupRestore(unittest.TestCase):
    def test_restore_no_existing_permissions(self):
        populate_local_keycloak.populate()
        rs = ResourceServer()

        backed_up_permissions = [
            uma_permission("test-dataset", "admin", [janedoe_user]),
            uma_permission("test-dataset", "update", [janedoe_user]),
            uma_permission("test-dataset", "write", [janedoe_user, someservice_client]),
            uma_permission("test-dataset", "read", [janedoe_user, homersimpson_user]),
        ]
        restore_permissions(rs, backed_up_permissions)

        restored_permissions = rs.list_permissions()
        assert len(restored_permissions) == len(backed_up_permissions)
        for backed_up_permission in backed_up_permissions:
            restored_permission = rs.get_permission(backed_up_permission["name"])
            del backed_up_permission["id"]
            del restored_permission["id"]
            self.assertDictEqual(backed_up_permission, restored_permission)

    def test_restore_changed_users(self):
        """Test that any changed users in backup are reflected during restore."""
        populate_local_keycloak.populate()
        rs = ResourceServer()

        existing_resource = "okdata:dataset:test-dataset"
        rs.create_resource(existing_resource, janedoe_user)
        rs.update_permission(existing_resource, "write", add_users=[someservice_client])

        backed_up_permissions = [
            uma_permission("test-dataset", "admin", [homersimpson_user]),
            uma_permission("test-dataset", "update", [homersimpson_user]),
            uma_permission("test-dataset", "write", [homersimpson_user]),
            uma_permission("test-dataset", "read", [homersimpson_user]),
        ]
        restore_permissions(rs, backed_up_permissions, skip_deleted_resources=True)

        restored_permissions = rs.list_permissions()

        assert len(restored_permissions) == 4
        for scope in ["admin", "update", "write", "read"]:
            assert set(rs.get_permission(f"{existing_resource}:{scope}")["users"]) == {
                homersimpson_user.user_id,
            }

    def test_restore_skip_deleted(self):
        """Test that any deleted resources are not restored."""
        populate_local_keycloak.populate()
        rs = ResourceServer()

        existing_resource = "okdata:dataset:test-dataset"
        rs.create_resource(existing_resource, janedoe_user)

        backed_up_permissions = [
            uma_permission("test-dataset", "admin", [janedoe_user]),
            uma_permission("test-dataset", "update", [janedoe_user]),
            uma_permission("test-dataset", "write", [janedoe_user]),
            uma_permission("test-dataset", "read", [janedoe_user]),
            uma_permission("some-other-dataset", "admin", [homersimpson_user]),
        ]
        restore_permissions(rs, backed_up_permissions, skip_deleted_resources=True)

        restored_permissions = rs.list_permissions()

        assert len(restored_permissions) == 4
        for scope in ["admin", "update", "write", "read"]:
            assert set(rs.get_permission(f"{existing_resource}:{scope}")["users"]) == {
                janedoe_user.user_id,
            }

import pytest

from dataplatform_keycloak.resource_server import ResourceServer
from dataplatform_keycloak.teams_client import TeamsClient
from jobs import monitor
from models import User
from tests.setup import (
    populate_local_keycloak,
    local_keycloak_config as kc_config,
)


@pytest.fixture
def mock_resource_server(mock_ssm_client):
    populate_local_keycloak.populate()

    resource_server = ResourceServer()
    janedoe = User.parse_obj({"user_id": kc_config.janedoe, "user_type": "user"})
    homer = User.parse_obj({"user_id": kc_config.homersimpson, "user_type": "user"})
    resource_server.create_resource("okdata:dataset:foo", owner=janedoe)
    resource_server.create_resource("okdata:dataset:bar", owner=homer)
    resource_server.update_permission(
        resource_name="okdata:dataset:foo",
        scope="okdata:dataset:read",
        add_users=[homer],
        remove_users=[],
    )
    return resource_server


def test_check_users(monkeypatch, mock_ssm_client, mock_resource_server, mocker):
    keycloak_admin = TeamsClient().teams_admin_client
    keycloak_users = keycloak_admin.get_users()
    permissions = mock_resource_server.list_permissions()
    keycloak_admin.delete_user(keycloak_admin.get_user_id(kc_config.homersimpson))

    monkeypatch.setattr(monitor, "load_latest_backup", lambda: permissions)
    monkeypatch.setattr(monitor, "slack_notify", lambda x: None)
    notifier = mocker.spy(monitor, "slack_notify")
    logger = mocker.spy(monitor, "log_add")

    monitor.check_users({}, {})

    logger.assert_any_call(keycloak_users_count=(len(keycloak_users) - 1))
    logger.assert_any_call(backed_up_permissions_count=len(permissions))
    logger.assert_any_call(missing_users_count=1)
    logger.assert_any_call(missing_users_usernames=[kc_config.homersimpson])
    notifier.assert_called_once()
    assert notifier.call_args.args[0].startswith(
        "1 Keycloak user(s) holding resource permissions"
    )


def test_check_users_no_deleted_user(
    monkeypatch, mock_ssm_client, mock_resource_server, mocker
):
    keycloak_admin = TeamsClient().teams_admin_client
    keycloak_users = keycloak_admin.get_users()
    permissions = mock_resource_server.list_permissions()

    monkeypatch.setattr(monitor, "load_latest_backup", lambda: permissions)
    monkeypatch.setattr(monitor, "slack_notify", lambda x: None)
    notifier = mocker.spy(monitor, "slack_notify")
    logger = mocker.spy(monitor, "log_add")

    monitor.check_users({}, {})

    logger.assert_any_call(keycloak_users_count=len(keycloak_users))
    logger.assert_any_call(backed_up_permissions_count=len(permissions))
    logger.assert_any_call(missing_users_count=0)
    notifier.assert_not_called()


def test_check_users_no_backup(
    monkeypatch, mock_ssm_client, mock_resource_server, mocker
):
    keycloak_admin = TeamsClient().teams_admin_client
    keycloak_users = keycloak_admin.get_users()

    monkeypatch.setattr(monitor, "load_latest_backup", lambda: None)
    monkeypatch.setattr(monitor, "slack_notify", lambda x: None)
    notifier = mocker.spy(monitor, "slack_notify")
    logger = mocker.spy(monitor, "log_add")

    monitor.check_users({}, {})

    logger.assert_any_call(keycloak_users_count=len(keycloak_users))
    notifier.assert_called_once()
    assert notifier.call_args.args[0].startswith("No permissions backup found")

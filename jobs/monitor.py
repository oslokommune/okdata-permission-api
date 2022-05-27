import os

import requests
from aws_xray_sdk.core import patch_all, xray_recorder
from okdata.aws.logging import logging_wrapper, log_add, log_exception

from dataplatform_keycloak.teams_client import TeamsClient
from jobs.backup import load_latest_backup


SLACK_PERMISSION_API_ALERTS_WEBHOOK_URL = os.environ[
    "SLACK_PERMISSION_API_ALERTS_WEBHOOK_URL"
]

patch_all()


@logging_wrapper
@xray_recorder.capture("check_users")
def check_users(event, context):
    """Get all users from permissions and notify about any deleted accounts.

    An attempt to mitigate issues caused by https://github.com/keycloak/keycloak/issues/11284
    (fixed in Keycloak 18).
    """

    keycloak_admin_client = TeamsClient().teams_admin_client
    keycloak_users = [user["username"] for user in keycloak_admin_client.get_users()]

    log_add(keycloak_users_count=len(keycloak_users))

    permissions = load_latest_backup()

    if permissions is None:
        slack_notify(
            "No permissions backup found while checking for deleted Keycloak users."
        )
        return

    log_add(backed_up_permissions_count=len(permissions))

    if len(permissions) == 0:
        return

    missing_users = identify_missing_users(permissions, keycloak_users)

    log_add(missing_users_count=len(missing_users))

    if len(missing_users) > 0:
        log_add(missing_users_usernames=missing_users)

        slack_notify(
            f"{len(missing_users)} Keycloak user(s) holding resource permissions identified "
            "as deleted. This causes an error while listing permissions and must be fixed "
            "manually by re-creating permissions for affected permissions using scripts "
            "available in the `okdata-permission-api` repo."
        )


def identify_missing_users(permissions, keycloak_users):
    permission_users = []

    for permission in permissions:
        for user in permission.get("users", []):
            if user not in permission_users:
                permission_users.append(user)

    return [user for user in permission_users if user not in keycloak_users]


def slack_notify(message):
    try:
        response = requests.post(
            SLACK_PERMISSION_API_ALERTS_WEBHOOK_URL, json={"text": message}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log_exception(e)

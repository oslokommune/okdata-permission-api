"""Script for restoring backed up UMA permissions.

This works by deleting and re-creating resources and permissions found in
specified backup file.

Note: This script assumes that Keycloak users and other relevant config are
backed up and restored separately.
"""

import argparse
import json
import logging
import os
import sys

import requests
from requests.exceptions import HTTPError

from dataplatform_keycloak.exceptions import ResourceNotFoundError
from dataplatform_keycloak.groups import TEAM_GROUP_PREFIX
from dataplatform_keycloak.resource_server import permission_description
from models import User, UserType
from models.scope import all_scopes_for_type, scope_permission
from resources.resource_util import (
    resource_name_from_permission_name,
    resource_type_from_resource_name,
)
from scripts.utils import resource_server_from_env

logger = logging.getLogger("restore_permissions_backup")


def read_input(input_path):
    with open(input_path) as f:
        return json.loads(f.read())


def get_users_from_permission(permission):
    return (
        [User(user_id=u, user_type=UserType.USER) for u in permission.get("users", [])]
        + [
            User(
                user_id=u[len(f"/{TEAM_GROUP_PREFIX}") :]
                if u.startswith(f"/{TEAM_GROUP_PREFIX}")
                else u,
                user_type=UserType.GROUP,
            )
            for u in permission.get("groups", [])
        ]
        + [
            User(user_id=u, user_type=UserType.CLIENT)
            for u in permission.get("clients", [])
        ]
    )


def create_resource(resource_server, resource_name):
    create_resource_response = requests.post(
        resource_server.uma_well_known.resource_registration_endpoint,
        json={
            "type": resource_type_from_resource_name(resource_name),
            "name": resource_name,
            "ownerManagedAccess": True,
            "scopes": all_scopes_for_type(
                resource_type_from_resource_name(resource_name)
            ),
        },
        headers=resource_server.request_headers(),
    )
    create_resource_response.raise_for_status()
    return create_resource_response.json()


def restore_permissions(
    resource_server, permissions, skip_deleted_resources=False, apply_changes=True
):
    logger.info("Restoring backed up permissions...")

    resources = {}

    for permission in permissions:
        resource_name = resource_name_from_permission_name(permission["name"])
        scope = permission["scopes"][0]
        users = get_users_from_permission(permission)
        resources.setdefault(resource_name, {})[scope] = users

    for resource_name, scopes in resources.items():
        logger.info(f"Re-creating resource {resource_name}")

        if apply_changes:
            try:
                resource_server.delete_resource(resource_name)
            except ResourceNotFoundError:
                if skip_deleted_resources:
                    logger.warning("Skipped previously deleted resource")
                    continue
            else:
                logger.debug(f"Deleted existing resource {resource_name}")

        logger.debug(f"Creating resource {resource_name}")
        if apply_changes:
            resource = create_resource(resource_server, resource_name)

        for scope, users in scopes.items():
            permission_name = f"{resource_name}:{scope_permission(scope)}"
            logger.info(
                f"Re-creating permission {permission_name} ({', '.join(f'{u.user_type}:{u.user_id}' for u in users)})"
            )
            if apply_changes:
                resource_server.create_permission(
                    permission_name=permission_name,
                    description=permission_description(scope, resource_name),
                    resource_id=resource["_id"],
                    scopes=[scope],
                    users=users,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore Keycloak permissions from file."
    )
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--input",
        required=True,
        help="Path to file containing backed up permissions",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )
    parser.add_argument("--skip-deleted-resources", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    apply_changes = args.apply
    skip_deleted_resources = args.skip_deleted_resources

    try:
        resource_server = resource_server_from_env(args.env)
    except HTTPError:
        logger.error(
            "Could not connect to Keycloak, server={}, realm={}".format(
                os.environ["KEYCLOAK_SERVER"],
                os.environ["KEYCLOAK_REALM"],
            )
        )
        sys.exit()

    logger.info(f"Backup file: {args.input}")

    backed_up_permissions = read_input(args.input)

    logger.info(f"Permissions count: {len(backed_up_permissions)}")
    logger.info(f"Skip deleted resources: {skip_deleted_resources}")
    logger.info(f"Dry run: {not apply_changes}")

    if (len(backed_up_permissions) == 0) or (input("Continue? [y/N] ").lower() != "y"):
        sys.exit("Aborted!")

    restore_permissions(
        resource_server,
        backed_up_permissions,
        skip_deleted_resources,
        apply_changes,
    )

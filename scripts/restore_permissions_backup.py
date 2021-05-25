import argparse
import json
import logging
import os
import sys

from boto3 import resource
from requests.exceptions import HTTPError

from dataplatform_keycloak import ResourceServer
from dataplatform_keycloak.ssm import SsmClient
from models import User, UserType
from resources.resource import resource_type, resource_name_from_permission_name
from sandbox import initialize_local_environment

logger = logging.getLogger("restore_permissions_backup")

# Script for restoring backed up UMA permissions.
# Note: This script assumes that Keycloak users and other relevant
# config are backed up and restored separately.


def read_input(input_path):
    with open(input_path) as f:
        return json.loads(f.read())


def get_users_from_permission(permission):
    return (
        [User(user_id=u, user_type=UserType.USER) for u in permission.get("users", [])]
        + [
            User(user_id=u, user_type=UserType.GROUP)
            for u in permission.get("groups", [])
        ]
        + [
            User(user_id=u, user_type=UserType.CLIENT)
            for u in permission.get("clients", [])
        ]
    )


def restore_permissions(resource_server, permissions, apply_changes=True):
    logger.info("Restoring backed up permissions...")

    resources = {}

    for permission in permissions:
        resource_name = resource_name_from_permission_name(permission["name"])
        scope = permission["scopes"][0]
        users = get_users_from_permission(permission)
        resources.setdefault(resource_name, {})[scope] = users

    for resource_name, scopes in resources.items():
        logger.info(f"Attempting to restore permissions for {resource_name}")

        admin_scope = resource_type(resource_name) + ":admin"
        owner = next(iter(scopes.get(admin_scope, [])), None)

        if not owner:
            logger.error(
                f"Could not restore permissions for {resource_name}: no owner found"
            )
            continue

        logger.info(f"Creating resource {resource_name}, owner={owner.user_id}")
        if apply_changes:
            try:
                resource_server.create_resource(resource_name, owner)
            except HTTPError as e:
                if e.response.status_code == 409:
                    logger.info(f"Resource {resource_name} already exists")
                else:
                    logger.exception(f"Could not create resource {resource}")
                    raise

        for scope, users in scopes.items():
            logger.info(
                f"Updating permissions for {resource_name}, "
                f"scope={scope}, users={','.join(u.user_id for u in users)}"
            )
            if apply_changes:
                resource_server.update_permission(
                    resource_name=resource_name,
                    scope=scope,
                    add_users=users,
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
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    os.environ["AWS_PROFILE"] = f"okdata-{args.env}"
    os.environ["AWS_REGION"] = "eu-west-1"

    apply_changes = args.apply

    if args.env == "local":
        initialize_local_environment()
    else:
        resource_server_client_id = "okdata-resource-server"
        os.environ["RESOURCE_SERVER_CLIENT_ID"] = resource_server_client_id
        os.environ["KEYCLOAK_REALM"] = "api-catalog"
        os.environ["KEYCLOAK_SERVER"] = SsmClient.get_secret(
            "/dataplatform/shared/keycloak-server-url"
        )
        os.environ["RESOURCE_SERVER_CLIENT_SECRET"] = SsmClient.get_secret(
            f"/dataplatform/{resource_server_client_id}/keycloak-client-secret"
        )

    logger.info(f"Environment: {args.env}")

    try:
        resource_server = ResourceServer()
    except HTTPError:
        logger.error(
            "Could not connect to Keycloak, server={}, realm={}".format(
                os.environ["KEYCLOAK_SERVER"],
                os.environ["KEYCLOAK_REALM"],
            )
        )
        sys.exit()

    logger.info(f"Keycloak server URL: {resource_server.keycloak_server_url}")
    logger.info(f"Keycloak realm: {resource_server.keycloak_realm}")
    logger.info(f"Backup file: {args.input}")

    backed_up_permissions = read_input(args.input)

    logger.info(f"Permissions to restore: {len(backed_up_permissions)}")
    logger.info(f"Dry run: {not apply_changes}")

    if (len(backed_up_permissions) == 0) or (input("Continue? [y/N] ").lower() != "y"):
        sys.exit("Aborted!")

    restore_permissions(resource_server, backed_up_permissions, apply_changes)

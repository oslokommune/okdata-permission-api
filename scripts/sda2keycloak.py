"""Script for migrating simple-dataset-authorizer permissions to Keycloak.

Expects list of dataset,principal_id combinations to migrate in input file.
"""

import argparse
import dataclasses
import json
import logging
import os
import sys
import time
from datetime import datetime

import boto3
from requests.exceptions import HTTPError

from dataplatform_keycloak import ResourceServer
from dataplatform_keycloak.exceptions import (
    ResourceNotFoundException,
    PermissionNotFoundException,
)
from dataplatform_keycloak.ssm import SsmClient
from models import User
from models.scope import all_scopes_for_type
from resources.resource import resource_type
from sandbox import initialize_local_environment
from tests.setup import populate_local_keycloak

logger = logging.getLogger("sda2keycloak")


@dataclasses.dataclass
class SDAItem:
    principal_id: str
    dataset_id: str

    @property
    def user_type(self):
        return "client" if self.principal_id.startswith("service-account-") else "user"

    @property
    def user_id(self):
        return (
            self.principal_id[len("service-account-") :]
            if self.user_type == "client"
            else self.principal_id
        )

    @classmethod
    def fromdict(cls, d):
        return cls(d["principalId"], d["datasetId"])


def get_all_items(table):
    response = table.scan()
    items = response["Items"]

    while "LastEvaluatedKey" in response:
        time.sleep(1)  # Let's be nice
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])

    return items


def read_input(input_path):
    with open(input_path) as f:
        return [
            {"datasetId": line.split(",")[0], "principalId": line.split(",")[1]}
            for line in f.read().splitlines()
        ]


def write_output(output_dir_path, results):
    output_json = json.dumps(results, indent=2)
    if output_dir_path:
        dt_now_iso = datetime.utcnow().isoformat()
        output_file = os.path.join(
            output_dir_path, f"sda2keycloak_result-{dt_now_iso}.json"
        )
        logger.info(f"Writing results to {output_file}")
        with open(output_file, "w+") as f:
            f.write(output_json)
    print(output_json)


class ResourceAlreadyExistsException(Exception):
    pass


def create_resource(server, name, owner, delete_first=False):
    if delete_first and apply_changes:
        try:
            logger.info(f"Deleting resource {name}")
            server.delete_resource(name)
        except ResourceNotFoundException:
            pass
    try:
        if apply_changes:
            server.create_resource(name, owner)
    except HTTPError as e:
        if e.response.status_code == 409:
            logger.info(f"Resource {name} already exists")
            raise ResourceAlreadyExistsException()
        logger.exception(f"Could not create resource {name}")
        raise
    logger.info(
        "Created resource {} (owner={}, type={})".format(
            name, owner.user_id, owner.user_type
        )
    )


def update_permissions(server, name, user):
    for scope in all_scopes_for_type(resource_type(name)):
        logger.info(
            "Updating permission {} for {} ({}) on {}".format(
                scope, user.user_id, user.user_type, name
            )
        )
        if apply_changes:
            server.update_permission(
                resource_name=resource_name,
                scope=scope,
                add_users=[user],
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--input",
        required=True,
        help="Path to line separated txt file with dataset and principal ids to be migrated",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Optional. Path to directory where you want output to be written",
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
    output_dir_path = args.output
    input_permissions = read_input(args.input)

    if args.env == "local":
        initialize_local_environment()
        populate_local_keycloak.populate()
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

    resource_server = ResourceServer()

    logger.info(f"Environment: {args.env}")
    logger.info(f"Keycloak server URL: {resource_server.keycloak_server_url}")
    logger.info(f"Keycloak realm: {resource_server.keycloak_realm}")

    if args.env == "local":
        # Items for testing against local instance of Keycloak
        sda_items = [
            {"principalId": "janedoe", "datasetId": "dodsrater-status"},
            {"principalId": "homersimpson", "datasetId": "dodsrater-status"},
            {"principalId": "janedoe", "datasetId": "bym-dbo-ladbar-motorvogn"},
            {
                "principalId": "service-account-some-service",
                "datasetId": "bym-dbo-ladbar-motorvogn",
            },
            # Resources with non-existing user as owner (i.e. no
            # permissions created, causing update_permission to fail)
            {"principalId": "janedoe2", "datasetId": "dode-hester"},
            {"principalId": "janedoe", "datasetId": "dode-hester"},
        ]
    else:
        dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
        sda_table = dynamodb.Table("simple-dataset-authorizer")
        sda_items = get_all_items(sda_table)

    permissions_to_migrate = []

    # Build list of permissions to migrate from input file,
    # ignoring duplicates and items not found in SDA table
    for item in input_permissions:
        if item in permissions_to_migrate:
            logger.warning(f"Ignored {','.join(item.values())} (duplicate)")
            continue

        if item not in sda_items:
            logger.warning(f"Permission {','.join(item.values())} not found in table")
            continue

        permissions_to_migrate.append(item)

    logger.info(
        "Found {} items to migrate (of {} in file)".format(
            len(permissions_to_migrate), len(input_permissions)
        )
    )

    if (len(permissions_to_migrate) == 0) or (input("Continue? [y/N] ").lower() != "y"):
        logger.info("Aborted!")
        sys.exit()

    results = {"updated_items": {}, "failed_items": {}}

    for item in map(SDAItem.fromdict, permissions_to_migrate):
        resource_name = f"okdata:dataset:{item.dataset_id}"
        user = User(user_id=item.user_id, user_type=item.user_type)

        logger.info(
            "Setting permissions for {} ({}) on {}".format(
                user.user_id, user.user_type, resource_name
            )
        )

        try:
            try:
                # Create resource and permissions
                create_resource(resource_server, resource_name, owner=user)

            except ResourceAlreadyExistsException:
                try:
                    # Update permissions for subsequent users
                    update_permissions(resource_server, resource_name, user)
                    results["updated_items"].setdefault(resource_name, []).append(
                        user.user_id
                    )

                except PermissionNotFoundException as e:
                    logger.error(e)
                    # Attempt re-creation of resource previously created
                    # with non-existent user as owner
                    if resource_name in results["updated_items"]:
                        results["failed_items"][resource_name] = results[
                            "updated_items"
                        ][resource_name]

                    create_resource(
                        resource_server, resource_name, owner=user, delete_first=True
                    )
                    results["updated_items"][resource_name] = [user.user_id]

                except HTTPError:
                    # KC returns 500 error="unknown_error" if user doesn't exist (?)
                    logger.exception(
                        "Could not update permissions {} ({}) on {}".format(
                            user.user_id, user.user_type, resource_name
                        )
                    )
                    results["failed_items"].setdefault(resource_name, []).append(
                        user.user_id
                    )
            else:
                results["updated_items"].setdefault(resource_name, []).append(
                    user.user_id
                )
        except Exception as e:
            logger.exception(e)
            logger.info("Aborted!")
            results["failed_items"].setdefault(resource_name, []).append(user.user_id)
            break

write_output(output_dir_path, results)

"""Script for migrating simple-dataset-authorizer permissions to Keycloak."""

import argparse
import dataclasses
import json
import logging
import os
import time
from datetime import datetime

from requests.exceptions import HTTPError
import boto3

from tests.setup import populate_local_keycloak
from dataplatform_keycloak import ResourceServer
from dataplatform_keycloak.ssm import SsmClient
from models import User
from models.scope import all_scopes_for_type
from resources.resource import resource_type
from sandbox import initialize_local_environment

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


def write_output(output_dir_path, output_json):
    dt_now_iso = datetime.utcnow().isoformat()
    output_file = os.path.join(
        output_dir_path, f"sda2keycloak_result-{dt_now_iso}.json"
    )
    logger.info(f"Writing results to {output_file}")
    with open(output_file, "w+") as f:
        f.write(output_json)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
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
        ]
    else:
        dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
        sda_table = dynamodb.Table("simple-dataset-authorizer")
        sda_items = get_all_items(sda_table)

    logger.info(f"Found {len(sda_items)} items in table")

    results = {"updated_items": {}, "failed_items": {}}

    for item in map(SDAItem.fromdict, sda_items):
        resource_name = f"okdata:dataset:{item.dataset_id}"
        user = User(user_id=item.user_id, user_type=item.user_type)
        scopes = all_scopes_for_type(resource_type(resource_name))

        permission = {
            "resource_name": resource_name,
            "owner": user,
        }

        logger.info(
            "Setting permissions for {} ({}) on {}".format(
                user.user_id, user.user_type, resource_name
            )
        )

        try:
            # Create resource and permissions
            if apply_changes:
                resource_server.create_resource(resource_name, owner=user)
        except HTTPError as e:
            if e.response.status_code != 409:
                raise

            # Update permissions for any additional user(s)
            for scope in scopes:
                try:
                    if apply_changes:
                        resource_server.update_permission(
                            resource_name=resource_name,
                            scope=scope,
                            add_users=[user],
                        )
                    logger.info(
                        "Updated permission {} for {} ({}) on {}".format(
                            scope, user.user_id, user.user_type, resource_name
                        )
                    )
                    results["updated_items"].setdefault(resource_name, {}).setdefault(
                        user.user_id, []
                    ).append(scope)
                except HTTPError:
                    # KC returns 500 error="unknown_error" if user doesn't exist (?)
                    logger.exception(
                        "Could not update permission {} for {} ({}) on {}".format(
                            scope, user.user_id, user.user_type, resource_name
                        )
                    )
                    results["failed_items"].setdefault(resource_name, {}).setdefault(
                        user.user_id, []
                    ).append(scope)

        else:
            logger.info(
                "Created resource {} with owner {} ({})".format(
                    resource_name, user.user_id, user.user_type
                )
            )
            results["updated_items"].setdefault(resource_name, {}).setdefault(
                user.user_id, scopes
            )

    output_json = json.dumps(results, indent=2)
    if output_dir_path:
        write_output(output_dir_path, output_json)
    print(output_json)

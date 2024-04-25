"""Script for listing permissions in Keycloak"""

import argparse
import json
import logging

from dataplatform_keycloak.exceptions import ResourceNotFoundError
from scripts.utils import resource_server_from_env


logger = logging.getLogger("list_permissions")


def print_output(permissions, output_file_path=None):
    serialized_permissions = json.dumps(permissions, indent=2)

    print(serialized_permissions)

    if output_file_path:
        with open(output_file_path, "w+") as f:
            f.write(serialized_permissions)
        logger.info(f"Output written to {output_file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--resource-name",
        required=False,
        help="Optional. Name of resource to list permissions for",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Optional. Path to file where you want output to be written",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    resource_server = resource_server_from_env(args.env)

    try:
        permissions = resource_server.list_permissions(resource_name=args.resource_name)
        print_output(permissions, args.output)
    except ResourceNotFoundError as e:
        print(e)

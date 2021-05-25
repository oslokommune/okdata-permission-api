"""Script for listing permissions for a resource in keycloak
"""

import argparse
import json
import logging

from scripts.utils import resource_server_from_env


logger = logging.getLogger("list_permissions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--resource-name",
        required=True,
        help="Name of resource to list permissions for",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    resource_server = resource_server_from_env(args.env)

    permissions = resource_server.list_permissions(resource_name=args.resource_name)

    print(json.dumps(permissions, indent=2))

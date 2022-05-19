"""Script for printing a single Keycloak permission."""

import argparse
import json
import logging

from scripts.utils import resource_server_from_env


logger = logging.getLogger("get_permission")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        required=True,
        choices=["local", "dev", "prod"],
    )
    parser.add_argument(
        "--permission-name", required=True, help="Name of resource to get"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=list(logging._nameToLevel.keys()),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    resource_server = resource_server_from_env(args.env)
    print(
        json.dumps(
            resource_server.get_permission(args.permission_name),
            indent=2,
        )
    )

"""Script for updating a Keycloak permission by raw JSON."""

import argparse
import json
import logging

from scripts.utils import resource_server_from_env

logger = logging.getLogger("update_permission_raw")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        required=True,
        choices=["local", "dev", "prod"],
    )
    parser.add_argument(
        "--permission-file",
        required=True,
        help="Name of file holding the permission",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=list(
            logging._nameToLevel.keys(),
        ),
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.getLevelName(args.log_level))

    with open(args.permission_file) as f:
        permission = json.loads(f.read())

    resource_server = resource_server_from_env(args.env)
    resource_server.update_permission_raw(permission)

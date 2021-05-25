"""Script for deleting a resource in keycloak
"""

import argparse
import logging

from scripts.utils import resource_server_from_env


logger = logging.getLogger("delete_resource")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--resource-name",
        required=True,
        help="Name of resource to delete",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )
    parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    resource_server = resource_server_from_env(args.env)

    if args.apply:
        status, message = resource_server.delete_resource(args.resource_name)
        if status == 204:
            print(f"Deleted resource: {args.resource_name}")
        else:
            print(message)
    else:
        print(f"Would have deleted resource: {args.resource_name}")

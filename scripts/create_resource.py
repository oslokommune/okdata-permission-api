"""Script for creating a new resource in keycloak
"""

import argparse
import json
import logging

from models import User, UserType
from scripts.utils import resource_server_from_env


logger = logging.getLogger("create_resource")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--resource-name",
        required=True,
        help="Name of resource to create",
    )
    parser.add_argument(
        "--owner-id",
        required=True,
        help="Identifier for user that will own the resource",
    )
    parser.add_argument(
        "--owner-type",
        required=True,
        help="Type of user that will own the resource",
        choices=[u.value for u in UserType],
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )
    parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    resource_server = resource_server_from_env(args.env)

    owner = User.parse_obj({"user_id": args.owner_id, "user_type": args.owner_type})

    if args.apply:
        result = resource_server.create_resource(args.resource_name, owner)
        print(f"Created resource: {json.dumps(result['resource'], indent=2)}")
        print(
            f"Created permissions for resource: {json.dumps(result['permissions'], indent=2)}"
        )
    else:
        print(
            f"Would have created resource: {args.resource_name}, with owner: {owner.json()}"
        )

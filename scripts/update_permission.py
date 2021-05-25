"""Script for updating permissions in keycloak.
"""

import argparse
import json
import logging

from models import User, UserType
from scripts.utils import resource_server_from_env

logger = logging.getLogger("update_permission")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
    parser.add_argument(
        "--resource-name",
        required=True,
        help="Name of resource to update permissions for",
    )
    parser.add_argument(
        "--scope",
        required=True,
        help="Name of scope to permissions for",
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="Identifier for a user",
    )
    parser.add_argument(
        "--user-type",
        required=True,
        help="Type of user",
        choices=[u.value for u in UserType],
    )
    parser.add_argument("--action", required=True, choices=["add", "remove"])
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )
    parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    resource_server = resource_server_from_env(args.env)

    user = User.parse_obj({"user_id": args.user_id, "user_type": args.user_type})
    users_to_add = [user] if args.action == "add" else []
    users_to_remove = [user] if args.action == "remove" else []

    if args.apply:
        updated_permission = resource_server.update_permission(
            resource_name=args.resource_name,
            scope=args.scope,
            add_users=users_to_add,
            remove_users=users_to_remove,
        )
        print("Successfully updated permission")
        print(json.dumps(updated_permission, indent=2))

    else:
        print(f"Resource name: {args.resource_name}")
        print(f"Scope: {args.scope}")
        print(f"Would add users: {[u.json() for u in users_to_add]}")
        print(f"Would remove users: {[u.json() for u in users_to_remove]}")

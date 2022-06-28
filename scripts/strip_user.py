"""Script for stripping a user of all permissions."""

import argparse

from models import OkdataPermission, User, UserType
from scripts.utils import resource_server_from_env

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["local", "dev", "prod"])
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
    parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    user = User.parse_obj({"user_id": args.user_id, "user_type": args.user_type})
    resource_server = resource_server_from_env(args.env)
    permissions = resource_server.list_permissions(**{user.user_type: user.user_id})

    if permissions:
        for p in map(OkdataPermission.from_uma_permission, permissions):
            if args.apply:
                resource_server.update_permission(
                    p.resource_name, p.scope, remove_users=[user]
                )
            else:
                print("[DRY RUN] ", end="")

            print(
                f"Removed {user.user_type} '{user.user_id}' from '{p.scope}' "
                f"on '{p.resource_name}'"
            )
    else:
        print(f"No permissions to delete for {user.user_type} '{user.user_id}'")

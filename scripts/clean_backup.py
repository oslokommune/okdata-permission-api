"""Script for replacing all permissions of a user with another user in provided backup file.

This is useful as a workaround for: https://github.com/keycloak/keycloak/issues/11284, which
causes an error when listing policies with remaining permissions for a user that has been
deleted from Keycloak.
"""

import argparse
import json
import logging
import sys

from dataplatform_keycloak.groups import team_name_to_group_name
from models import User, UserType

logger = logging.getLogger("clean_backup")


def read_input(input_path):
    with open(input_path) as f:
        permissions = json.loads(f.read())
    logger.info(f"Read {len(permissions)} permissions from file")
    return permissions


def write_output(output_path, permissions):
    logger.info(f"Writing results to {output_path}")
    with open(output_path, "w+") as f:
        f.write(json.dumps(permissions, indent=2))
    logger.info(f"Wrote {len(permissions)} permissions to file")


def replace_user(permissions, user, replacement_user, include_unchanged=True):
    user_list_keys = {
        UserType.USER: "users",
        UserType.GROUP: "groups",
        UserType.CLIENT: "clients",
    }

    # Prefix user ids of type group (i.e. team)
    user.user_id = (
        user.user_id
        if user.user_type != UserType.GROUP
        else "/" + team_name_to_group_name(user.user_id)
    )
    replacement_user.user_id = (
        replacement_user.user_id
        if replacement_user.user_type != UserType.GROUP
        else "/" + team_name_to_group_name(replacement_user.user_id)
    )

    for permission in permissions:
        if user.user_id in permission.get(user_list_keys[user.user_type], []):
            permission[user_list_keys[user.user_type]].remove(user.user_id)

            # Note: Keycloak seems to delete the permission if it encouters
            # an empty user/group/client list (?).
            if len(permission[user_list_keys[user.user_type]]) == 0:
                del permission[user_list_keys[user.user_type]]

            if replacement_user.user_id not in permission.get(
                user_list_keys[replacement_user.user_type], []
            ):
                permission.setdefault(
                    user_list_keys[replacement_user.user_type], []
                ).append(replacement_user.user_id)

            logger.info(
                'Replaced "{}:{}" with "{}:{}" in "{}"'.format(
                    user.user_type,
                    user.user_id,
                    replacement_user.user_type,
                    replacement_user.user_id,
                    permission["name"],
                )
            )

            yield permission

        else:
            if include_unchanged:
                yield permission


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="commands", dest="command")

    remove_user_parser = subparsers.add_parser(
        "replace-user", help="Replace user in all permission"
    )
    remove_user_parser.add_argument(
        "--user-id",
        required=True,
        help="Identifier for a user to replace",
    )
    remove_user_parser.add_argument(
        "--user-type",
        required=True,
        help="Type of user",
        choices=[u.value for u in UserType],
    )
    remove_user_parser.add_argument(
        "--replacement-user-id",
        required=True,
        help="Identifier for a replacement user",
    )
    remove_user_parser.add_argument(
        "--replacement-user-type",
        required=True,
        help="Type of replacement user",
        choices=[u.value for u in UserType],
    )
    remove_user_parser.add_argument(
        "--changed-permissions-only",
        action="store_true",
        help="Only include changed permissions in output",
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to file containing permissions to clean",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to file where you want the output to be written",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=list(logging._nameToLevel.keys())
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    if not args.command:
        sys.exit("Nothing to do!")

    input_permissions = read_input(args.input)

    if args.command == "replace-user":
        permissions = list(
            replace_user(
                input_permissions,
                User.parse_obj({"user_id": args.user_id, "user_type": args.user_type}),
                User.parse_obj(
                    {
                        "user_id": args.replacement_user_id,
                        "user_type": args.replacement_user_type,
                    }
                ),
                include_unchanged=not args.changed_permissions_only,
            )
        )

    write_output(args.output, permissions)

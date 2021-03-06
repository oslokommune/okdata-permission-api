"""Utilities for Keycloak group handling."""

TEAM_GROUP_PREFIX = "TEAM-"
TEAM_ATTRIBUTE_PREFIX = TEAM_GROUP_PREFIX


def group_name_to_team_name(group_name):
    """Return the team name corresponding to Keycloak's `group_name`."""
    if is_team_group(group_name):
        return group_name[len(TEAM_GROUP_PREFIX) :]
    return group_name


def team_name_to_group_name(team_name):
    """Return the Keycloak group name corresponding to `team_name`."""
    return f"{TEAM_GROUP_PREFIX}{team_name}"


def is_team_group(group_name):
    """Test if a group is considered a team by evaluating `group_name`.

    A team group is denoted by a special prefix defined by `TEAM_GROUP_PREFIX`.
    """
    return group_name.startswith(TEAM_GROUP_PREFIX)


def group_ids(groups):
    """Return list of group IDs from list of groups."""
    return [group["id"] for group in groups]


# Aliases for the group<->team mapping functions. We want to handle group
# attributes in the same way. As long as TEAM_GROUP_PREFIX ==
# TEAM_ATTRIBUTE_PREFIX, the implementations are identical.
group_attribute_to_team_attribute = group_name_to_team_name
team_attribute_to_group_attribute = team_name_to_group_name
is_team_attribute = is_team_group

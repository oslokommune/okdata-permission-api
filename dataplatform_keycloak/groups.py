"""Utilities for Keycloak group handling."""


def group_name_to_team_name(group_name):
    """Return the team name corresponding to Keycloak's `group_name`."""
    if group_name.startswith("TEAM-"):
        return group_name[len("TEAM-") :]

    return group_name


def team_name_to_group_name(team_name):
    """Return the Keycloak group name corresponding to `team_name`."""
    return f"TEAM-{team_name}"

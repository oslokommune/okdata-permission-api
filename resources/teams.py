from typing import List, Union

from fastapi import APIRouter, Depends, status

from dataplatform_keycloak.exceptions import (
    TeamNameExistsError,
    TeamNotFoundError,
    TeamsServerError,
    UserNotFoundError,
)
from dataplatform_keycloak.groups import group_ids
from dataplatform_keycloak.teams_client import TeamsClient
from models import Team, TeamMember, UpdateTeamBody
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models


router = APIRouter(dependencies=[Depends(AuthInfo)])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[Team],
    response_model_exclude_unset=True,
)
def get_teams(
    include: Union[str, None] = None,
    has_role: Union[str, None] = None,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(auth_info.principal_id)
        teams = teams_client.list_teams(realm_role=has_role)
        groups = group_ids(user_teams)
        for team in teams:
            team["is_member"] = team["id"] in groups

    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )

    return teams if include == "all" else [team for team in teams if team["is_member"]]


@router.get(
    "/{team_id}",
    status_code=status.HTTP_200_OK,
    response_model=Team,
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
    ),
)
def get_team(
    team_id: str,
    has_role: Union[str, None] = None,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(auth_info.principal_id)
        team = teams_client.get_team(team_id, realm_role=has_role)
        team["is_member"] = team["id"] in group_ids(user_teams)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )
    return team


@router.get(
    "/name/{team_name}",
    status_code=status.HTTP_200_OK,
    response_model=Team,
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
    ),
)
def get_team_by_name(
    team_name: str,
    has_role: Union[str, None] = None,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(auth_info.principal_id)
        team = teams_client.get_team_by_name(team_name, realm_role=has_role)
        team["is_member"] = team["id"] in group_ids(user_teams)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )
    return team


@router.get(
    "/{team_id}/members",
    status_code=status.HTTP_200_OK,
    response_model=List[TeamMember],
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
    ),
)
def get_team_members(
    team_id: str,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        return teams_client.get_team_members(team_id)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )


@router.patch(
    "/{team_id}",
    status_code=status.HTTP_200_OK,
    response_model=Team,
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
def update_team(
    team_id: str,
    body: UpdateTeamBody,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(auth_info.principal_id)
        team = teams_client.get_team(team_id)
        if team["id"] not in group_ids(user_teams):
            raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")
        team = teams_client.update_team(team_id, body.name, body.attributes)
        team["is_member"] = True
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamNameExistsError:
        raise ErrorResponse(
            status.HTTP_409_CONFLICT, "A team with that name already exists"
        )
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )
    return team


@router.put(
    "/{team_id}/members",
    status_code=status.HTTP_200_OK,
    response_model=List[TeamMember],
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
    ),
)
def update_members(
    team_id: str,
    body: List[str],
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(auth_info.principal_id)
        team = teams_client.get_team(team_id)
        if team["id"] not in group_ids(user_teams):
            raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")
        return teams_client.update_members(team_id, body)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except UserNotFoundError as e:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, str(e))
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )


@router.get(
    "/users/{username}",
    status_code=status.HTTP_200_OK,
    response_model=TeamMember,
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
    ),
)
def get_user_by_username(
    username: str,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        return teams_client.get_user_by_username(username)
    except UserNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "User not found")
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )


@router.get(
    "/users/{username}/teams",
    status_code=status.HTTP_200_OK,
    response_model=List[Team],
    response_model_exclude_unset=True,
)
def get_teams_by_username(
    username: str,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    """List teams in which the user given by `username` is a member."""
    try:
        username_teams = teams_client.list_user_teams(username)
        user_teams = teams_client.list_user_teams(auth_info.principal_id)
        groups = group_ids(user_teams)

        for team in username_teams:
            team["is_member"] = team["id"] in groups

        return username_teams

    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )

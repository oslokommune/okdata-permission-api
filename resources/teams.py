from typing import List, Optional

from fastapi import APIRouter, Depends, status

from dataplatform_keycloak.exceptions import TeamNotFoundError, TeamsServerError
from dataplatform_keycloak.groups import group_ids
from dataplatform_keycloak.teams_client import TeamsClient
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models
from models import Team, TeamMember


router = APIRouter(dependencies=[Depends(AuthInfo)])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[Team],
    responses=error_message_models(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_teams(
    has_role: Optional[str] = None,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(username=auth_info.principal_id)
        teams = teams_client.list_teams(realm_role=has_role)
    except TeamsServerError:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    return [team for team in teams if team["id"] in group_ids(user_teams)]


@router.get(
    "/{team_id}",
    status_code=status.HTTP_200_OK,
    response_model=Team,
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_team(
    team_id: str,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(username=auth_info.principal_id)
        team = teams_client.get_team(team_id)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    if team["id"] not in group_ids(user_teams):
        raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")
    return team

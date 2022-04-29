from typing import List, Optional

from fastapi import APIRouter, Depends, status

from dataplatform_keycloak.exceptions import TeamNotFoundError, TeamsServerError
from dataplatform_keycloak.teams_client import TeamsClient
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models
from models import Team, TeamMember


router = APIRouter(dependencies=[Depends(AuthInfo)])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[Team],
    responses=error_message_models(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_teams(
    has_role: Optional[str] = None,
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        return teams_client.list_teams(realm_role=has_role)
    except TeamsServerError:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")


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
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        return teams_client.get_team(team_id)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")


@router.get(
    "/{team_id}/members",
    status_code=status.HTTP_200_OK,
    response_model=List[TeamMember],
    responses=error_message_models(
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_team_members(
    team_id: str,
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        return teams_client.get_team_members(team_id)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

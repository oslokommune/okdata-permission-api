import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from keycloak.exceptions import KeycloakError, KeycloakGetError
from requests.exceptions import HTTPError

from dataplatform_keycloak.exceptions import GroupNotTeamException
from dataplatform_keycloak.teams_client import TeamsClient
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models
from models import Team, TeamMember

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))

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
        teams = teams_client.list_teams(realm_role=has_role)
    except KeycloakGetError:
        return []
    except KeycloakError as e:
        keycloak_response = e.response
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    return [Team.parse_obj(team) for team in teams]


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
    except (KeycloakGetError, GroupNotTeamException):
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except KeycloakError as e:
        keycloak_response = e.response
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
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
    except (KeycloakGetError, GroupNotTeamException):
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except HTTPError as e:
        keycloak_response = e.response
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

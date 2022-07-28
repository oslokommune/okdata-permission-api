from typing import List, Union

from fastapi import APIRouter, Depends, status

from dataplatform_keycloak.exceptions import TeamNotFoundError, TeamsServerError
from dataplatform_keycloak.groups import group_ids
from dataplatform_keycloak.teams_client import TeamsClient
from models import Team, TeamMember
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models


router = APIRouter(dependencies=[Depends(AuthInfo)])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[Team],
    response_model_exclude_unset=True,
    responses=error_message_models(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_teams(
    has_role: Union[str, None] = None,
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
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_team(
    team_id: str,
    has_role: Union[str, None] = None,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        user_teams = teams_client.list_user_teams(username=auth_info.principal_id)
        team = teams_client.get_team(team_id, realm_role=has_role)
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    if team["id"] not in group_ids(user_teams):
        raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")
    return team


# TODO: This is not restricted to members of the team like the other
#       endpoints. They could also be opened like this one for symmetry.
@router.get(
    "/name/{team_name}",
    status_code=status.HTTP_200_OK,
    response_model=Team,
    responses=error_message_models(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_team_by_name(
    team_name: str,
    has_role: Union[str, None] = None,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        team = teams_client.get_team_by_name(team_name)
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
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_team_members(
    team_id: str,
    auth_info: AuthInfo = Depends(),
    teams_client: TeamsClient = Depends(TeamsClient),
):
    try:
        return [
            TeamMember(
                user_id=m["id"],
                username=m["username"],
                name=(
                    " ".join([m.get("firstName", ""), m.get("lastName", "")]).strip()
                    or None
                ),
                email=m.get("email"),
            )
            for m in teams_client.get_team_members(team_id)
        ]
    except TeamNotFoundError:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, "Team not found")
    except TeamsServerError:
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )

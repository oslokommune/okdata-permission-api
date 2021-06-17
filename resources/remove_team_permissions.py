import os
import logging

from fastapi import Depends, APIRouter, status
from requests.exceptions import HTTPError

from dataplatform_keycloak.resource_server import ResourceServer
from models import User, UserType, OkdataPermission
from resources.authorizer import AuthInfo, has_scope_permission
from resources.errors import ErrorResponse, error_message_models

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def resource_server():
    return ResourceServer()


router = APIRouter()


@router.put(
    "/{team_name}",
    dependencies=[Depends(has_scope_permission("okdata:team:admin"))],
    status_code=status.HTTP_200_OK,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR
    ),
)
def remove_team_from_permissions(
    team_name: str,
    auth_info: AuthInfo = Depends(),
    resource_server: ResourceServer = Depends(resource_server),
):
    """Return all permissions associated with the logged in user"""

    try:
        permissions = [
            OkdataPermission.from_uma_permission(permission)
            for permission in resource_server.list_permissions(team=team_name)
        ]

        team_user = User(user_id=team_name, user_type=UserType.GROUP)
        for permission in permissions:
            logger.info(f"remove {team_user.user_id} from {permission.resource_name}")
            resource_server.update_permission(
                resource_name=permission.resource_name,
                scope=permission.scope,
                remove_users=[team_user],
            )
        return {"message": f"Removed all permissions associated with {team_name}"}
    except HTTPError as e:
        keycloak_response = e.response
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
        raise ErrorResponse(500, "Server error")

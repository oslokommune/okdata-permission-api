import os
import logging

from fastapi import Depends, APIRouter, status
from requests.exceptions import HTTPError

from dataplatform_keycloak.resource_server import ResourceServer
from models import MyPermissionsResponse
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def resource_server():
    return ResourceServer()


router = APIRouter()


@router.get(
    "",
    dependencies=[Depends(AuthInfo)],
    status_code=status.HTTP_200_OK,
    response_model=MyPermissionsResponse,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR
    ),
)
def get_my_permissions(
    resource_server: ResourceServer = Depends(resource_server),
    auth_info: AuthInfo = Depends(),
):
    """Return all permissions associated with the logged in user"""

    try:
        try:
            user_permissions = resource_server.get_user_permissions(
                auth_info.bearer_token
            )
        except HTTPError as e:
            if e.response.status_code == 403:
                return MyPermissionsResponse.parse_obj({})
            logger.info(f"Keycloak response status code: {e.response.status_code}")
            logger.info(f"Keycloak response body: {e.response.text}")
            raise

        return MyPermissionsResponse.parse_obj(
            {
                permission["rsname"]: {"scopes": permission["scopes"]}
                for permission in user_permissions
            }
        )
    except Exception as e:
        logger.exception(e)
        raise ErrorResponse(500, "Server error")

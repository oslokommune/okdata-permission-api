import logging
import os

from fastapi import APIRouter, Depends, Path, status
from requests.exceptions import HTTPError

from dataplatform_keycloak.exceptions import (
    CannotRemoveOnlyAdminException,
    ResourceNotFoundError,
)
from dataplatform_keycloak.resource_server import ResourceServer
from models import OkdataPermission, UpdatePermissionBody
from resources.authorizer import has_resource_permission
from resources.errors import ErrorResponse, error_message_models

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def resource_server():
    return ResourceServer()


router = APIRouter()


@router.put(
    "/{resource_name}",
    dependencies=[Depends(has_resource_permission("admin"))],
    status_code=status.HTTP_200_OK,
    response_model=OkdataPermission,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def update_permission(
    body: UpdatePermissionBody,
    resource_name: str = Path(pattern=r"^[a-zA-Z0-9_:-]+$"),
    resource_server: ResourceServer = Depends(resource_server),
):
    try:
        updated_permission = resource_server.update_permission(
            resource_name=resource_name,
            scope=body.scope,
            add_users=body.add_users,
            remove_users=body.remove_users,
        )
    except CannotRemoveOnlyAdminException:
        raise ErrorResponse(
            status.HTTP_400_BAD_REQUEST, "Cannot remove the only admin for resource"
        )
    except HTTPError as e:
        keycloak_response = e.response
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")
    except Exception as e:
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    if "error" in updated_permission:
        raise ErrorResponse(
            status.HTTP_400_BAD_REQUEST, updated_permission["error_description"]
        )

    return OkdataPermission.from_uma_permission(updated_permission)


@router.get(
    "/{resource_name}",
    dependencies=[Depends(has_resource_permission("admin"))],
    status_code=status.HTTP_200_OK,
    response_model=list[OkdataPermission],
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def get_permissions(
    resource_name: str = Path(pattern=r"^[a-zA-Z0-9_:-]+$"),
    resource_server: ResourceServer = Depends(resource_server),
):
    try:
        return [
            OkdataPermission.from_uma_permission(p)
            for p in resource_server.list_permissions(resource_name)
        ]
    except HTTPError as e:
        keycloak_response = e.response
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")
    except ResourceNotFoundError as e:
        raise ErrorResponse(status.HTTP_404_NOT_FOUND, str(e))

import logging
import os

from fastapi import APIRouter, Depends, Path, status
from requests.exceptions import HTTPError

from dataplatform_keycloak.exceptions import CannotRemoveOnlyAdminException
from dataplatform_keycloak.resource_server import ResourceServer
from models import CreateResourceBody, OkdataPermission, UpdatePermissionBody
from resources.authorizer import has_resource_permission, has_permission
from resources.errors import ErrorResponse, error_message_models

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def resource_server():
    return ResourceServer()


router = APIRouter()


@router.post(
    "",
    dependencies=[Depends(has_permission("keycloak:resource:admin"))],
    status_code=status.HTTP_201_CREATED,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        status.HTTP_409_CONFLICT,
    ),
)
def create_resource(
    body: CreateResourceBody,
    resource_server: ResourceServer = Depends(resource_server),
):
    try:
        resource_server.create_resource(body.resource_name, body.owner)
    except HTTPError as e:
        keycloak_response = e.response
        if keycloak_response.status_code == 409:
            error_msg = keycloak_response.json()["error_description"]
            raise ErrorResponse(status.HTTP_409_CONFLICT, error_msg)
        logger.info(f"Keycloak response status code: {keycloak_response.status_code}")
        logger.info(f"Keycloak response body: {keycloak_response.text}")
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")
    except Exception as e:
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    return {"message": "Created"}


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
    resource_name: str = Path(..., regex=r"^[a-zA-Z0-9_:#-]+$"),
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
        status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR
    ),
)
def get_permissions(
    resource_name: str = Path(..., regex=r"^[a-zA-Z0-9_:#-]+$"),
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


@router.delete(
    "/{resource_name}",
    dependencies=[Depends(has_permission("keycloak:resource:admin"))],
    status_code=status.HTTP_200_OK,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def delete_resource(
    resource_name: str = Path(..., regex=r"^[a-zA-Z0-9_:#-]+$"),
    resource_server: ResourceServer = Depends(resource_server),
):
    try:
        resource_server.delete_resource(resource_name)
    except HTTPError as e:
        logger.info(f"Keycloak response status code: {e.response.status_code}")
        logger.info(f"Keycloak response body: {e.response.text}")
        logger.exception(e)
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Server error",
        )

    return {"message": "Deleted"}

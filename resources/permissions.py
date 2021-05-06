import logging
import os
from requests.exceptions import HTTPError
from typing import List

from fastapi import Depends, APIRouter, status

from dataplatform_keycloak import ResourceServer, CannotRemoveOnlyAdminException
from models import CreateResourceBody, OkdataPermission, UpdatePermissionBody
from resources.authorizer import has_resource_permission, has_resource_type_permission
from resources.errors import ErrorResponse, error_message_models

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def resource_server():
    return ResourceServer()


router = APIRouter()


# TODO: Ensure that resource exists
@router.post(
    "",
    dependencies=[Depends(has_resource_type_permission("create"))],
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
    resource_name: str,
    body: UpdatePermissionBody,
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
    except Exception as e:
        logger.exception(e)
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    return OkdataPermission.from_uma_permission(updated_permission)


@router.get(
    "/{resource_name}",
    dependencies=[Depends(has_resource_permission("admin"))],
    status_code=status.HTTP_200_OK,
    response_model=List[OkdataPermission],
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR
    ),
)
def get_permissions(
    resource_name: str,
    resource_server: ResourceServer = Depends(resource_server),
):
    return [
        OkdataPermission.from_uma_permission(p)
        for p in resource_server.list_permissions(resource_name)
    ]

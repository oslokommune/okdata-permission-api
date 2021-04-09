from typing import List

from fastapi import Depends, APIRouter, status

from dataplatform_keycloak import ResourceServer
from models import CreateResourceBody, OkdataPermission, UpdatePermissionBody
from resources.authorizer import (
    AuthInfo,
    has_resource_permission,
    has_resource_type_permission,
)
from resources.errors import ErrorResponse, error_message_models


def resource_server():
    return ResourceServer()


router = APIRouter()


# TODO: Ensure that resource exists
@router.post(
    "/",
    dependencies=[Depends(has_resource_type_permission("create"))],
    status_code=status.HTTP_201_CREATED,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR
    ),
)
def create_resource(
    body: CreateResourceBody,
    resource_server: ResourceServer = Depends(resource_server),
):
    try:
        resource_server.create_resource(body.resource_name, body.owner)
    #  TODO: log exception
    except Exception:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    return {"message": "Created"}


@router.put(
    "/{resource_name}",
    dependencies=[Depends(has_resource_permission("admin"))],
    status_code=status.HTTP_200_OK,
    response_model=OkdataPermission,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
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
    except Exception:
        raise ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error")

    return OkdataPermission.from_uma_permission(updated_permission)


# TODO: Find out if this information should be open to all logged in users
@router.get(
    "",
    dependencies=[Depends(AuthInfo)],
    status_code=status.HTTP_200_OK,
    response_model=List[OkdataPermission],
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR
    ),
)
def list_permissions(
    resource_name: str = None,
    team_id: str = None,
    scope: str = None,
    first: str = None,
    max_result: str = None,
    resource_server: ResourceServer = Depends(resource_server),
):
    uma_permissions = resource_server.list_permissions(
        resource_name=resource_name,
        group=team_id,
        scope=scope,
        first=first,
        max_result=max_result,
    )

    return [
        OkdataPermission.from_uma_permission(permission)
        for permission in uma_permissions
    ]

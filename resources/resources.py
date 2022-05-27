import logging
import os

from fastapi import APIRouter, Depends, Path, status
from requests.exceptions import HTTPError

from dataplatform_keycloak.resource_server import ResourceServer
from models import CreateResourceBody
from resources.authorizer import has_permission
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
    resource_name: str = Path(..., regex=r"^[a-zA-Z0-9_:-]+$"),
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

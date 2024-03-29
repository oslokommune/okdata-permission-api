import os
import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak import KeycloakOpenID
from okdata.resource_auth import ResourceAuthorizer
from requests.exceptions import HTTPError

from dataplatform_keycloak.ssm import SsmClient
from resources.errors import ErrorResponse
from resources.resource_util import resource_type_from_resource_name

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def keycloak_client():
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ.get("CLIENT_SECRET") or SsmClient.get_secret(
        f"/dataplatform/{client_id}/keycloak-client-secret"
    )
    return KeycloakOpenID(
        realm_name=os.environ["KEYCLOAK_REALM"],
        server_url=f"{os.environ['KEYCLOAK_SERVER']}/auth/",
        client_id=os.environ["CLIENT_ID"],
        client_secret_key=client_secret,
    )


def resource_authorizer() -> ResourceAuthorizer:
    return ResourceAuthorizer()


http_bearer = HTTPBearer(scheme_name="KeycloakToken")


class AuthInfo:
    principal_id: str
    bearer_token: str

    def __init__(
        self,
        authorization: HTTPAuthorizationCredentials = Depends(http_bearer),
        keycloak_client=Depends(keycloak_client),
    ):
        introspected = keycloak_client.introspect(authorization.credentials)

        if not introspected["active"]:
            raise ErrorResponse(401, "Invalid access token")

        self.principal_id = introspected["username"]
        self.bearer_token = authorization.credentials


def has_scope_permission(scope: str):
    def _verify_permission(
        auth_info: AuthInfo = Depends(),
        resource_authorizer: ResourceAuthorizer = Depends(resource_authorizer),
    ):
        """Pass through without exception if the user has specified `scope`."""
        try:
            if not resource_authorizer.has_access(
                auth_info.bearer_token,
                scope,
            ):
                raise ErrorResponse(403, "Forbidden")
        except HTTPError as e:
            error_response = e.response
            if error_response.status_code == 400:
                error_msg = error_response.json().get(
                    "error_description", "Bad request"
                )
                raise ErrorResponse(400, error_msg)

            logger.exception(e)
            raise ErrorResponse(500, "Server error")

    return _verify_permission


def has_resource_permission(permission: str):
    def _verify_permission(
        resource_name,
        auth_info: AuthInfo = Depends(),
        resource_authorizer: ResourceAuthorizer = Depends(resource_authorizer),
    ):
        """Pass through without exception if the user has permission.

        Check `permission` for `resource_name`
        (scope = "resource-name#resource-type:permission").
        """
        if resource_authorizer.has_access(
            auth_info.bearer_token, "keycloak:resource:admin"
        ):
            return

        try:
            if not resource_authorizer.has_access(
                auth_info.bearer_token,
                f"{resource_type_from_resource_name(resource_name)}:{permission}",
                resource_name,
            ):
                raise ErrorResponse(403, "Forbidden")
        except HTTPError as e:
            error_response = e.response
            if error_response.status_code == 400:
                error_msg = error_response.json().get(
                    "error_description", "Bad request"
                )
                raise ErrorResponse(400, error_msg)

            logger.exception(e)
            raise ErrorResponse(500, "Server error")

    return _verify_permission

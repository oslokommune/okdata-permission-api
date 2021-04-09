import os

from fastapi import Body, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak import KeycloakOpenID

from dataplatform_keycloak import ResourceAuthorizer, SsmClient
from models import CreateResourceBody
from resources.errors import ErrorResponse
from resources.resource import resource_type


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


http_bearer = HTTPBearer(scheme_name="Keycloak token")


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


def has_resource_type_permission(permission):
    def _verify_permission(
        body=Body(None),
        auth_info: AuthInfo = Depends(),
        resource_authorizer: ResourceAuthorizer = Depends(resource_authorizer),
    ):
        """Pass through without exception if the user has access.

        Check `permission` for the resource type belonging to `resource_name`
        from the request body (scope = "#resource-type:permission").
        """
        create_resource_body = CreateResourceBody.parse_obj(body)
        if not resource_authorizer.has_access(
            auth_info.bearer_token,
            f"{resource_type(create_resource_body.resource_name)}:{permission}",
        ):
            raise ErrorResponse(403, "Forbidden")

    return _verify_permission


def has_resource_permission(permission):
    def _verify_permission(
        resource_name,
        auth_info: AuthInfo = Depends(),
        resource_authorizer: ResourceAuthorizer = Depends(resource_authorizer),
    ):
        """Pass through without exception if the user has permission.

        Check `permission` for `resource_name`
        (scope = "resource-name#resource-type:permission").
        """
        if not resource_authorizer.has_access(
            auth_info.bearer_token,
            f"{resource_type(resource_name)}:{permission}",
            resource_name,
        ):
            raise ErrorResponse(403, "Forbidden")

    return _verify_permission

import os
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from keycloak import KeycloakOpenID

from models import ResourceScope
from .errors import ErrorResponse
from dataplatform_keycloak import SsmClient, ResourceAuthorizer


def keycloak_client():
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ.get("CLIENT_SECRET") or SsmClient.get_secret(
        f"/dataplatform/{client_id}/client_secret"
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


def dataset_owner(
    dataset_id: str,
    auth_info: AuthInfo = Depends(),
    resource_authorizer: ResourceAuthorizer = Depends(resource_authorizer),
):
    dataset_access = resource_authorizer.has_access(
        dataset_id, ResourceScope.owner, auth_info.bearer_token
    )
    if not dataset_access:
        raise ErrorResponse(403, "Forbidden")


def create_resource_access(
    auth_info: AuthInfo = Depends(),
    resource_authorizer: ResourceAuthorizer = Depends(resource_authorizer),
):

    access = resource_authorizer.create_resource_access(auth_info.bearer_token)

    if not access:
        raise ErrorResponse(403, "Forbidden")

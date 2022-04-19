import os
from typing import List, Optional
import logging
from datetime import datetime

import jwt
import requests
from keycloak import KeycloakOpenID
from requests.models import PreparedRequest

from dataplatform_keycloak.exceptions import (
    PermissionNotFoundException,
    ResourceNotFoundException,
    CannotRemoveOnlyAdminException,
    ConfigurationError,
)
from dataplatform_keycloak.groups import team_name_to_group_name
from dataplatform_keycloak.ssm import SsmClient
from dataplatform_keycloak.uma_well_known import get_well_known
from models import User, UserType
from models.scope import all_scopes_for_type, scope_permission
from resources.resource import resource_type

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


class ResourceServer:
    MAX_ITEMS_PER_PAGE = 300

    def __init__(
        self,
        client_secret_key=os.environ.get("RESOURCE_SERVER_CLIENT_SECRET"),
        keycloak_server_url=os.environ.get("KEYCLOAK_SERVER"),
        keycloak_realm=os.environ.get("KEYCLOAK_REALM"),
        resource_server_client_id=os.environ.get("RESOURCE_SERVER_CLIENT_ID"),
    ):
        if not keycloak_realm:
            raise ConfigurationError("keycloak_realm is not set")
        if not keycloak_server_url:
            raise ConfigurationError("keycloak_server_url is not set")
        if not resource_server_client_id:
            raise ConfigurationError("resource_server_client_id is not set")

        self.resource_server_client_id = resource_server_client_id
        self.keycloak_server_url = keycloak_server_url
        self.keycloak_realm = keycloak_realm

        if client_secret_key is None:
            client_secret_key = SsmClient.get_secret(
                f"/dataplatform/{self.resource_server_client_id}/keycloak-client-secret"
            )

        self.resource_server_client = KeycloakOpenID(
            realm_name=self.keycloak_realm,
            server_url=f"{self.keycloak_server_url}/auth/",
            client_id=self.resource_server_client_id,
            client_secret_key=client_secret_key,
        )

        self.uma_well_known = get_well_known(keycloak_server_url, keycloak_realm)

        self.resource_server_token = None

    def create_resource(self, resource_name: str, owner: Optional[User] = None):
        scopes = all_scopes_for_type(resource_type(resource_name))

        create_resource_response = requests.post(
            self.uma_well_known.resource_registration_endpoint,
            json={
                "type": resource_type(resource_name),
                "name": resource_name,
                "ownerManagedAccess": True,
                "scopes": scopes,
            },
            headers=self.request_headers(),
        )
        create_resource_response.raise_for_status()
        resource = create_resource_response.json()

        permissions = (
            [
                self.create_permission(
                    permission_name=f"{resource_name}:{scope_permission(scope)}",
                    description=permission_description(scope, resource_name),
                    resource_id=resource["_id"],
                    scopes=[scope],
                    users=[owner],
                )
                for scope in scopes
            ]
            if owner
            else []
        )

        return {
            "resource": resource,
            "permissions": permissions,
        }

    def create_permission(
        self,
        permission_name: str,
        description: str,
        resource_id: str,
        scopes: list,
        users: List[User],
        decision_strategy: str = "AFFIRMATIVE",
        logic: str = "POSITIVE",
    ):
        user_map = {o: [] for o in UserType}
        for user in users:
            user_map[user.user_type].append(user.user_id)

        permission = {
            "name": permission_name,
            "description": description,
            "scopes": scopes,
            "groups": list(map(team_name_to_group_name, user_map[UserType.GROUP])),
            "users": user_map[UserType.USER],
            "clients": user_map[UserType.CLIENT],
            "logic": logic,
            "decisionStrategy": decision_strategy,
        }

        create_permission_url = f"{self.uma_well_known.policy_endpoint}/{resource_id}"
        logger.info(f"POST {create_permission_url}")
        resp = requests.post(
            create_permission_url,
            headers=self.request_headers(),
            json=permission,
        )
        return resp.json()

    def update_permission(
        self,
        resource_name: str,
        scope: str,
        add_users: List[User] = [],
        remove_users: List[User] = [],
    ):
        permission_name = f"{resource_name}:{scope_permission(scope)}"

        try:
            permission = self.get_permission(permission_name)

            users, groups, clients = (
                set(permission.get("users", [])),
                set(permission.get("groups", [])),
                set(permission.get("clients", [])),
            )
            # Add if not present
            for user in add_users:
                if user.user_type is UserType.USER:
                    users.add(user.user_id)
                elif user.user_type is UserType.GROUP:
                    groups.add(team_name_to_group_name(user.user_id))
                elif user.user_type is UserType.CLIENT:
                    clients.add(user.user_id)

            # Remove if present
            for user in remove_users:
                if user.user_type is UserType.USER:
                    users.discard(user.user_id)
                elif user.user_type is UserType.GROUP:
                    groups.discard(f"/{team_name_to_group_name(user.user_id)}")
                elif user.user_type is UserType.CLIENT:
                    clients.discard(user.user_id)

            if scope_permission(scope) == "admin" and not any([users, groups, clients]):
                raise CannotRemoveOnlyAdminException

            permission["users"] = list(users)
            permission["groups"] = list(groups)
            permission["clients"] = list(clients)

            update_permission_url = (
                f"{self.uma_well_known.policy_endpoint}/{permission['id']}"
            )
            logger.info(f"PUT {update_permission_url}")

            resp = requests.put(
                update_permission_url,
                headers=self.request_headers(),
                json=permission,
            )
            resp.raise_for_status()

            if any([users, groups, clients]):
                # Return the "real" updated permission from Keycloak.
                return self.get_permission(permission_name)

            # Permission was deleted. Return our synthesized one for the user's
            # convenience.
            return permission

        except PermissionNotFoundException as e:
            if add_users:
                return self.create_permission(
                    permission_name=permission_name,
                    description=permission_description(scope, resource_name),
                    resource_id=self.get_resource_id(resource_name),
                    scopes=[scope],
                    users=add_users,
                )
            else:
                raise e

    def get_permission(self, permission_name):

        get_permission_url = (
            f"{self.uma_well_known.policy_endpoint}/?name={permission_name}"
        )
        logger.info(f"GET {get_permission_url}")
        resp = requests.get(get_permission_url, headers=self.request_headers())
        resp.raise_for_status()
        for permission in resp.json():
            if permission["name"] == permission_name:
                return permission
        raise PermissionNotFoundException(f"Permission {permission_name} not found")

    def _get(self, url, params):
        request = PreparedRequest()
        request.prepare(
            method="GET", url=url, headers=self.request_headers(), params=params
        )
        logger.info(f"GET {request.url}")
        resp = requests.Session().send(request)
        resp.raise_for_status()
        return resp.json()

    def _get_permissions(self, params={}):
        """Yield every permission from Keycloak matching `params`.

        The queries to Keycloak are paginated based on `MAX_ITEMS_PER_PAGE`.
        """
        url = f"{self.uma_well_known.policy_endpoint}/"
        query_params = {
            **params,
            "max": self.MAX_ITEMS_PER_PAGE,
            "first": 0,
        }

        while True:
            permissions = self._get(url, query_params)

            if permissions:
                for permission in permissions:
                    yield permission
                query_params["first"] += len(permissions)
            else:
                return

    def list_permissions(
        self,
        resource_name: str = None,
        scope: str = None,
        user: str = None,
        team: str = None,
        client: str = None,
    ):
        """Return a list of permissions matching the given parameters.

        By default (when no parameters are given), every permission is
        returned.
        """
        query_params = {}
        if resource_name:
            resource_id = self.get_resource_id(resource_name)
            query_params["resource"] = resource_id
        if scope:
            query_params["scope"] = scope

        permissions = self._get_permissions(query_params)

        # Keycloak doesn't support querying by these parameters directly, so we
        # need to filter by them manually after querying Keycloak.
        if user:
            permissions = [p for p in permissions if user in p.get("users", [])]
        if team:
            permissions = [
                p
                for p in permissions
                if f"/{team_name_to_group_name(team)}" in p.get("groups", [])
            ]
        if client:
            permissions = [p for p in permissions if client in p.get("clients", [])]

        return list(permissions)

    def delete_permission(self, permission_name):

        permission_id = self.get_permission(permission_name)["id"]
        delete_url = f"{self.uma_well_known.policy_endpoint}/{permission_id}"
        logger.info(f"DELETE {delete_url}")
        resp = requests.delete(delete_url, headers=self.request_headers())
        return resp.status_code, resp.text

    def delete_resource(self, resource_name):

        resource_id = self.get_resource_id(resource_name)
        delete_url = (
            f"{self.uma_well_known.resource_registration_endpoint}/{resource_id}"
        )
        logger.info(f"DELETE {delete_url}")
        resp = requests.delete(
            delete_url,
            headers=self.request_headers(),
        )
        return resp.status_code, resp.text

    def get_resource_id(self, resource_name):

        get_id_url = (
            f"{self.uma_well_known.resource_registration_endpoint}?name={resource_name}"
        )
        logger.info(f"GET {get_id_url}")
        resp = requests.get(get_id_url, headers=self.request_headers())
        for resource_id in resp.json():
            get_resource_url = (
                f"{self.uma_well_known.resource_registration_endpoint}/{resource_id}"
            )
            logger.info(f"GET {get_resource_url}")
            resource = requests.get(
                get_resource_url, headers=self.request_headers()
            ).json()
            if resource["name"] == resource_name:
                return resource["_id"]
        raise ResourceNotFoundException(f"No resource named {resource_name}")

    def get_user_permissions(self, user_bearer_token, scope: str = None):

        """
        Request a urn:ietf:params:oauth:grant-type:uma-ticket rpt from resource server
        and returns a decoded value with all permissions associated with the rpt
        https://github.com/keycloak/keycloak-documentation/blob/master/authorization_services/topics/service-authorization-uma-authz-process.adoc
        http://www.keycloak.org/docs/latest/authorization_services/index.html#_service_obtaining_permissions
        """

        payload = [
            ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
            ("audience", self.resource_server_client_id),
        ]
        if scope:
            payload.append(("permission", f"#{scope}"))

        headers = {
            "Authorization": f"Bearer {user_bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(
            self.uma_well_known.token_endpoint, data=payload, headers=headers
        )

        response.raise_for_status()
        uma_ticket_access_token = response.json()["access_token"]
        return jwt.decode(
            uma_ticket_access_token,
            options={"verify_signature": False, "verify_aud": False},
        )["authorization"]["permissions"]

    def request_headers(self):
        return {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }

    def resource_server_access_token(self):
        if self.resource_server_token is None:
            self.resource_server_token = self.resource_server_client.token(
                grant_type=["client_credentials"]
            )["access_token"]
        else:
            if token_is_expired(self.resource_server_token):
                self.resource_server_token = self.resource_server_client.token(
                    grant_type=["client_credentials"]
                )["access_token"]
        return self.resource_server_token


def permission_description(scope, resource_name):
    return "Allows for {} operations on resource: {}".format(
        scope_permission(scope),
        resource_name,
    )


def token_is_expired(token):
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    expires_timestamp = decoded_token["exp"]
    expires_dt = datetime.utcfromtimestamp(expires_timestamp)

    difference = expires_dt - datetime.utcnow()

    # Ensure that the token will not expire before it is used in a request
    return difference.total_seconds() < 10

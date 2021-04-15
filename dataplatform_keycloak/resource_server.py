import os
from typing import List
import logging

import requests
from keycloak import KeycloakOpenID
from requests.models import PreparedRequest

from dataplatform_keycloak.ssm import SsmClient
from dataplatform_keycloak.uma_well_known import get_well_known
from models import User, UserType
from models.scope import all_scopes_for_type, scope_permission
from resources.resource import resource_type

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


class ResourceServer:
    def __init__(self):

        self.keycloak_server_url = os.environ["KEYCLOAK_SERVER"]
        self.keycloak_realm = os.environ["KEYCLOAK_REALM"]
        self.resource_server_client_id = os.environ["RESOURCE_SERVER_CLIENT_ID"]

        client_secret_key = os.environ.get("RESOURCE_SERVER_CLIENT_SECRET", None)

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

        self.uma_well_known = get_well_known(
            self.keycloak_server_url, self.keycloak_realm
        )

        self.resource_server_token = None

    def create_resource(self, resource_name: str, owner: User):
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

        permissions = [
            self.create_permission(
                permission_name=f"{resource_name}:{scope_permission(scope)}",
                description="Allows for {} operations on resource: {}".format(
                    scope_permission(scope),
                    resource_name,
                ),
                resource_id=resource["_id"],
                scopes=[scope],
                owner=owner,
            )
            for scope in scopes
        ]

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
        owner: User,
        decision_strategy: str = "AFFIRMATIVE",
        logic: str = "POSITIVE",
    ):
        owner_map = {o: [] for o in UserType}
        owner_map[owner.user_type].append(owner.user_id)

        permission = {
            "name": permission_name,
            "description": description,
            "scopes": scopes,
            "groups": owner_map[UserType.GROUP],
            "users": owner_map[UserType.USER],
            "clients": owner_map[UserType.CLIENT],
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
                groups.add(user.user_id)
            elif user.user_type is UserType.CLIENT:
                clients.add(user.user_id)

        # Remove if present
        for user in remove_users:
            if user.user_type is UserType.USER:
                users.discard(user.user_id)
            elif user.user_type is UserType.GROUP:
                groups.discard(user.user_id)
            elif user.user_type is UserType.CLIENT:
                clients.discard(user.user_id)

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
        return self.get_permission(permission_name)

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
        raise Exception(f"Permission {permission_name} not found")

    def list_permissions(
        self,
        resource_name=None,
        group=None,
        scope: str = None,
        first: int = None,
        max_result: int = None,
    ):
        query_params = {}
        if resource_name:
            resource_id = self.get_resource_id(resource_name)
            query_params["resource"] = resource_id
        if scope:
            query_params["scope"] = scope
        if first:
            query_params["first"] = first
        if max_result:
            query_params["max"] = max_result

        get_permission_url = f"{self.uma_well_known.policy_endpoint}/"
        list_permissions_request = PreparedRequest()
        list_permissions_request.prepare(
            method="GET",
            url=get_permission_url,
            headers=self.request_headers(),
            params=query_params,
        )

        logger.info(f"GET {list_permissions_request.url}")
        resp = requests.Session().send(list_permissions_request)
        resp.raise_for_status()

        if group:
            return [
                permission
                for permission in resp.json()
                if f"/{group}" in permission["groups"]
            ]

        return resp.json()

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
        raise Exception(f"No resource named {resource_name}")

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

        return self.resource_server_token

import requests
from requests.models import PreparedRequest
from typing import List
import os
from keycloak import KeycloakOpenID
from .uma_well_known import get_well_known
from .ssm import SsmClient
from models import UserType, ResourceScope, User


class ResourceServer:
    keycloak_server_url = os.environ["KEYCLOAK_SERVER"]
    keycloak_realm = os.environ["KEYCLOAK_REALM"]
    resource_server_client_id = os.environ["RESOURCE_SERVER_CLIENT_ID"]

    def __init__(self):

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

    def create_dataset_resource(self, dataset_id: str, owner: User):
        create_resource_response = requests.post(
            self.uma_well_known.resource_registration_endpoint,
            json={
                "type": "okdata:dataset",
                "name": dataset_id,
                "ownerManagedAccess": True,
                "scopes": [
                    ResourceScope.read.value,
                    ResourceScope.write.value,
                    ResourceScope.update.value,
                    ResourceScope.owner.value,
                ],
            },
            headers=self.request_headers(),
        )
        create_resource_response.raise_for_status()
        dataset_resource = create_resource_response.json()
        resource_id = dataset_resource["_id"]

        owner_permission = self.create_permission(
            permission_name=f"{dataset_id}:owner",
            description=f"Allows for owner operations on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.owner.value],
            owner=owner,
        )
        read_permission = self.create_permission(
            permission_name=f"{dataset_id}:read",
            description=f"Allows for read on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.read.value],
            owner=owner,
        )
        write_permission = self.create_permission(
            permission_name=f"{dataset_id}:write",
            description=f"Allows for write on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.write.value],
            owner=owner,
        )
        update_permission = self.create_permission(
            permission_name=f"{dataset_id}:update",
            description=f"Allows for update on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.update.value],
            owner=owner,
        )
        return {
            "resource": dataset_resource,
            "permissions": [
                owner_permission,
                read_permission,
                write_permission,
                update_permission,
            ],
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
        print(f"POST {create_permission_url}")
        resp = requests.post(
            create_permission_url,
            headers=self.request_headers(),
            json=permission,
        )
        return resp.json()

    def update_permission(
        self,
        resource_name: str,
        scope: ResourceScope,
        add_users: List[User] = [],
        remove_users: List[User] = [],
    ):

        permission = self.get_permission(
            f"{resource_name}:{scope.value.split(':')[-1]}"
        )

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
                groups.add(user.user_id)

        # Remove if not present
        for user in remove_users:
            if user.user_type is UserType.USER:
                users.discard(user.user_id)
            elif user.user_type is UserType.GROUP:
                groups.discard(user.user_id)
            elif user.user_type is UserType.CLIENT:
                groups.discard(user.user_id)

        permission["users"] = list(users)
        permission["groups"] = list(groups)
        permission["clients"] = list(clients)

        update_permission_url = (
            f"{self.uma_well_known.policy_endpoint}/{permission['id']}"
        )
        print(f"PUT {update_permission_url}")

        resp = requests.put(
            update_permission_url,
            headers=self.request_headers(),
            json=permission,
        )
        resp.raise_for_status()
        return self.get_permission(f"{resource_name}:{scope.value.split(':')[-1]}")

    def get_permission(self, permission_name):

        get_permission_url = (
            f"{self.uma_well_known.policy_endpoint}/?name={permission_name}"
        )
        print(f"GET {get_permission_url}")
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
        scope: ResourceScope = None,
        first: int = None,
        max_result: int = None,
    ):
        query_params = {}
        if resource_name:
            resource_id = self.get_resource_id(resource_name)
            query_params["resource"] = resource_id
        if scope:
            query_params["scope"] = scope.value
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

        print(f"GET {list_permissions_request.url}")
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
        print(f"DELETE {delete_url}")
        resp = requests.delete(delete_url, headers=self.request_headers())
        return resp.status_code, resp.text

    def delete_resource(self, resource_name):

        resource_id = self.get_resource_id(resource_name)
        delete_url = (
            f"{self.uma_well_known.resource_registration_endpoint}/{resource_id}"
        )
        print(f"DELETE {delete_url}")
        resp = requests.delete(
            delete_url,
            headers=self.request_headers(),
        )
        return resp.status_code, resp.text

    def get_resource_id(self, resource_name):

        get_id_url = (
            f"{self.uma_well_known.resource_registration_endpoint}?name={resource_name}"
        )
        print(f"GET {get_id_url}")
        resp = requests.get(get_id_url, headers=self.request_headers())
        for resource_id in resp.json():
            get_resource_url = (
                f"{self.uma_well_known.resource_registration_endpoint}/{resource_id}"
            )
            print(f"GET {get_resource_url}")
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

    def sandbox(self, param):
        # resource_id = self.get_resource_id(param)
        get_permission_url = f"{self.uma_well_known.policy_endpoint}/"
        print(f"GET {get_permission_url}")
        resp = requests.get(get_permission_url, headers=self.request_headers())
        return resp.json()

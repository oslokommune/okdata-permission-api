import requests
import os
from enum import Enum
from pprint import PrettyPrinter
from keycloak import KeycloakOpenID
from dp_keycloak.uma_utils import get_well_known
from dp_keycloak.ssm import get_secret

pp = PrettyPrinter(indent=2)


class ResourceScope(Enum):
    read = "ok:origo:dataset:read"
    write = "ok:origo:dataset:write"
    update = "ok:origo:dataset:update"
    owner = "ok:origo:dataset:owner"


class ResourceServer:
    keycloak_server_url = os.environ["KEYCLOAK_SERVER"]
    keycloak_realm = os.environ["KEYCLOAK_REALM"]
    resource_server_name = os.environ["RESOURCE_SERVER_CLIENT_ID"]

    def __init__(self):

        self.resource_server_client = KeycloakOpenID(
            realm_name=self.keycloak_realm,
            server_url=f"{self.keycloak_server_url}/auth/",
            client_id=self.resource_server_name,
            client_secret_key=get_secret(
                "/dataplatform/poc-policy-server/client_secret"
            ),  # os.environ["RESOURCE_SERVER_CLIENT_SECRET"],
        )

        self.uma_well_known = get_well_known(
            self.keycloak_server_url, self.keycloak_realm
        )

        self.resource_server_token = None

    def create_dataset_resource(self, dataset_id, owner):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }
        body = {
            "type": f"ok:origo:dataset",
            "name": dataset_id,
            "ownerManagedAccess": True,
            "scopes": [
                ResourceScope.read.value,
                ResourceScope.write.value,
                ResourceScope.update.value,
                ResourceScope.owner.value,
            ],
        }
        dataset_resource = requests.post(
            self.uma_well_known.resource_registration_endpoint,
            json=body,
            headers=headers,
        ).json()
        resource_id = dataset_resource["_id"]
        owner_permission = self.create_permission(
            permission_name=f"{dataset_id}-owner",
            description=f"Allows for owner operations on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.owner.value],
            groups=[owner],
            decisionStrategy="UNANIMOUS",
        )
        read_permission = self.create_permission(
            permission_name=f"{dataset_id}-read",
            description=f"Allows for read on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.read.value],
            groups=[owner],
            decisionStrategy="AFFIRMATIVE",
        )
        write_permission = self.create_permission(
            permission_name=f"{dataset_id}-write",
            description=f"Allows for write on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.write.value],
            groups=[owner],
            decisionStrategy="AFFIRMATIVE",
        )
        update_permission = self.create_permission(
            permission_name=f"{dataset_id}-update",
            description=f"Allows for write on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScope.update.value],
            groups=[owner],
            decisionStrategy="AFFIRMATIVE",
        )
        return {
            "resource": dataset_resource,
            "permissions": [
                owner_permission,
                read_permission,
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
        decisionStrategy: str,
        logic="POSITIVE",
        groups: list = [],
        users: list = [],
    ):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }
        permission = {
            "name": permission_name,
            "description": description,
            "scopes": scopes,
            "groups": groups,
            "users": users,
            "logic": logic,
            "decisionStrategy": decisionStrategy,
        }

        create_permission_url = f"{self.uma_well_known.policy_endpoint}/{resource_id}"
        print(f"POST {create_permission_url}")
        resp = requests.post(create_permission_url, headers=headers, json=permission,)
        return resp.json()

    def update_permission(
        self,
        resource_name,
        scope,
        user_to_add: str = None,
        group_to_add: str = None,
        decicion_strategy: str = None,
    ):

        permission = self.get_permission(
            f"{resource_name}-{scope.value.split(':')[-1]}"
        )

        if user_to_add:
            users = permission.get("users", [])
            users.append(user_to_add)
            permission["users"] = users

        if group_to_add:
            groups = permission.get("groups", [])
            groups.append(group_to_add)
            permission["groups"] = groups

        if decicion_strategy:
            permission["decisionStrategy"] = decicion_strategy

        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }

        update_permission_url = (
            f"{self.uma_well_known.policy_endpoint}/{permission['id']}"
        )
        print(f"PUT {update_permission_url}")

        resp = requests.put(update_permission_url, headers=headers, json=permission,)
        resp.raise_for_status()
        return self.get_permission(f"{resource_name}-{scope.value.split(':')[-1]}")

    def get_permission(self, permission_name):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }
        get_permission_url = (
            f"{self.uma_well_known.policy_endpoint}/?name={permission_name}"
        )
        print(f"GET {get_permission_url}")
        resp = requests.get(get_permission_url, headers=headers)
        for permission in resp.json():
            if permission["name"] == permission_name:
                return permission
        raise Exception(f"Permission {permission_name} not found")

    def delete_permission(self, permission_name):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }
        permission_id = self.get_permission(permission_name)["id"]
        delete_url = f"{self.uma_well_known.policy_endpoint}/{permission_id}"
        print(f"DELETE {delete_url}")
        resp = requests.delete(delete_url, headers=headers)
        return resp.status_code, resp.text

    def delete_resource(self, resource_name):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }
        resource_id = self.get_resource_id(resource_name)
        delete_url = (
            f"{self.uma_well_known.resource_registration_endpoint}/{resource_id}"
        )
        print(f"DELETE {delete_url}")
        resp = requests.delete(delete_url, headers=headers,)
        return resp.status_code, resp.text

    def get_resource_id(self, resource_name):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }

        get_id_url = (
            f"{self.uma_well_known.resource_registration_endpoint}?name={resource_name}"
        )
        print(f"GET {get_id_url}")
        resp = requests.get(get_id_url, headers=headers)
        for resource_id in resp.json():
            get_resource_url = (
                f"{self.uma_well_known.resource_registration_endpoint}/{resource_id}"
            )
            print(f"GET {get_resource_url}")
            resource = requests.get(get_resource_url, headers=headers).json()
            if resource["name"] == resource_name:
                return resource["_id"]

    def resource_server_access_token(self):
        if self.resource_server_token is None:
            self.resource_server_token = self.resource_server_client.token(
                grant_type=["client_credentials"]
            )["access_token"]

        return self.resource_server_token

    def sandbox(self, param):
        headers = {
            "Authorization": f"Bearer {self.resource_server_access_token()}",
            "Content-Type": "application/json",
        }
        resource_id = self.get_resource_id(param)
        get_permission_url = (
            f"{self.uma_well_known.policy_endpoint}/?resource={resource_id}"
        )
        print(f"GET {get_permission_url}")
        resp = requests.get(get_permission_url, headers=headers)
        return resp.json()

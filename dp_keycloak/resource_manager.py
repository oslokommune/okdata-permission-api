import requests
import os
from enum import Enum
import json
from pprint import PrettyPrinter
from keycloak import KeycloakOpenID, KeycloakAdmin
from dp_keycloak.uma_utils import get_well_known

pp = PrettyPrinter(indent=2)


class ResourceScopes(Enum):
    read = "ok:origo:dataset:read"
    write = "ok:origo:dataset:write"
    update = "ok:origo:dataset:update"
    owner = "ok:origo:dataset:owner"


class ResourceServer:
    keycloak_server_url = os.environ["KEYCLOAK_SERVER"]
    keycloak_realm = os.environ["KEYCLOAK_REALM"]
    resource_server_name = (os.environ["RESOURCE_SERVER_CLIENT_ID"],)

    user_id = "janedoe"
    user_password = os.environ["JANEDOE_PW"]

    def __init__(self):

        self.resource_server_client = KeycloakOpenID(
            realm_name=self.keycloak_realm,
            server_url=f"{self.keycloak_server_url}/auth/",
            client_id=self.resource_server_name,
            client_secret_key=os.environ["RESOURCE_SERVER_CLIENT_SECRET"],
        )

        self.kc_admin = KeycloakAdmin(
            server_url=f"{self.keycloak_server_url}/auth/",
            username=os.environ["KC_ADMIN_USERNAME"],
            password=os.environ["KC_ADMIN_PW"],
            realm_name=self.keycloak_realm,
            verify=True,
        )
        self.resource_server_uuid = self.kc_admin.get_client_id(
            self.resource_server_name
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
                ResourceScopes.read.value,
                ResourceScopes.write.value,
                ResourceScopes.update.value,
                ResourceScopes.owner.value,
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
            scopes=[ResourceScopes.owner.value],
            groups=[owner],
        )
        read_permission = self.create_permission(
            permission_name=f"{dataset_id}-read",
            description=f"Allows for read on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScopes.read.value],
            groups=[owner],
        )
        write_permission = self.create_permission(
            permission_name=f"{dataset_id}-write",
            description=f"Allows for write on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScopes.write.value],
            groups=[owner],
        )
        update_permission = self.create_permission(
            permission_name=f"{dataset_id}-update",
            description=f"Allows for write on dataset: {dataset_id}",
            resource_id=resource_id,
            scopes=[ResourceScopes.update.value],
            groups=[owner],
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

    def evaluate(self, resource_name, scope: ResourceScopes, username):
        resource_id = self.get_resource_id(resource_name)
        user_id = self.kc_admin.get_user_id(username)
        evaluate_body = {
            "resources": [
                {
                    "name": resource_name,
                    "type": "ok:origo:dataset",
                    "owner": {
                        "id": "***REMOVED***",
                        "name": "poc-resource-server",
                    },
                    "ownerManagedAccess": True,
                    "_id": resource_id,
                    "uris": [],
                    "scopes": [scope.value],
                }
            ],
            "context": {"attributes": {}},
            "roleIds": [],
            "userId": user_id,
            "entitlements": False,
        }
        evaluate_path = "admin/realms/api-catalog/clients/***REMOVED***/authz/resource-server/policy/evaluate"
        print(f"POST {evaluate_path}")
        response = self.kc_admin.raw_post(
            path=evaluate_path, data=json.dumps(evaluate_body)
        )
        print(response.status_code)
        return response.json()

    def create_permission(
        self,
        permission_name: str,
        description: str,
        resource_id: str,
        scopes: list,
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
            "decisionStrategy": "UNANIMOUS",
        }

        create_permission_url = f"{self.uma_well_known.policy_endpoint}/{resource_id}"
        print(f"POST {create_permission_url}")
        resp = requests.post(create_permission_url, headers=headers, json=permission,)
        return resp.json()

    def update_permission(
        self,
        resource_name,
        scope,
        caller_user_id,
        user_to_add: str = None,
        group_to_add: str = None,
        decicion_strategy: str = None,
    ):

        evaluation = self.evaluate(resource_name, ResourceScopes.owner, caller_user_id)
        if evaluation["status"] != "PERMIT":
            raise Exception(
                f"{caller_user_id} not authorized for {ResourceScopes.owner.value} on {resource_name}"
            )

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
        return resp.status_code, resp.text

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


resource_server = ResourceServer()
# pp.pprint(resource_server.create_dataset_resource("kebab-rating", "TEAM-Ingrids Team"))
# pp.pprint(create_read_permission("my-first-dataset", "7be8c282-b664-4ce0-a9e2-a6b0781d46b9", "janedoe"))
# pp.pprint(give_permission("37ffa59c-ccb9-4731-8161-4903f2eedd4b", "homersimpson"))
# pp.pprint(delete_permission("885488bf-2176-4b5a-82fc-953c06feb8ce"))
# pp.pprint(resource_server.get_permission("kebab-rating-read"))
# print(delete_resource("7de0197b-185c-4124-a747-347d23e26d26"))
# print(get_resource_id("badetemperatur"))

# r = resource_server.evaluate("kebab-rating", ResourceScopes.read, "janedoe")
# pp.pprint(r)
# print(resource_server.resource_server_uuid)
# print(kc_admin.connection.base_url)

# pp.pprint(resource_server.sandbox("kebab-rating"))

print(
    resource_server.update_permission(
        "kebab-rating", ResourceScopes.read, "janedoe", decicion_strategy="AFFIRMATIVE"
    )
)

import os

import jwt
import requests

from dataplatform_keycloak.uma_well_known import get_well_known
from models import ResourceScope


class ResourceAuthorizer:
    def __init__(self):
        self.keycloak_server_url = os.environ["KEYCLOAK_SERVER"]
        self.keycloak_realm = os.environ["KEYCLOAK_REALM"]
        self.uma_well_known = get_well_known(
            self.keycloak_server_url, self.keycloak_realm
        )
        self.resource_server_name = os.environ["RESOURCE_SERVER_CLIENT_ID"]

    def has_access(self, resource_name, scope: ResourceScope, bearer_token):

        payload = [
            ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
            ("audience", self.resource_server_name),
            ("response_mode", "decision"),
            ("permission", f"{resource_name}#{scope.value}"),
        ]
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(
            self.uma_well_known.token_endpoint, data=payload, headers=headers
        )

        if response.status_code == 403:
            return False

        response.raise_for_status()

        return response.json()["result"]

    def create_resource_access(self, bearer_token: str):
        payload = [
            ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
            ("audience", self.resource_server_name),
            ("response_mode", "decision"),
            ("permission", "#createResource"),
        ]

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(
            self.uma_well_known.token_endpoint, data=payload, headers=headers
        )

        if response.status_code == 403:
            return False

        response.raise_for_status()

        return response.json()["result"]

    def get_user_permissions(self, user_bearer_token, scope: ResourceScope = None):
        payload = [
            ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
            ("audience", self.resource_server_name),
        ]
        if scope:
            payload.append(("permission", f"#{scope.value}"))

        headers = {
            "Authorization": f"Bearer {user_bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(
            self.uma_well_known.token_endpoint, data=payload, headers=headers
        )

        response.raise_for_status()

        access_token = response.json()["access_token"]
        return jwt.decode(access_token, verify=False)["authorization"]["permissions"]

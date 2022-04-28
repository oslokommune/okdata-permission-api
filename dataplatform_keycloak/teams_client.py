import logging
import os
from typing import Optional

from keycloak import KeycloakAdmin
from keycloak.urls_patterns import URL_ADMIN_REALM_ROLES
from keycloak.exceptions import (
    KeycloakError,
    KeycloakGetError,
    raise_error_from_response,
)

from dataplatform_keycloak.exceptions import (
    ConfigurationError,
    TeamNotFoundError,
    TeamsServerError,
)
from dataplatform_keycloak.groups import is_team_group
from dataplatform_keycloak.ssm import SsmClient

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


class TeamsClient:
    MAX_ITEMS_PER_PAGE = 300

    def __init__(
        self,
        keycloak_server_url=os.environ.get("KEYCLOAK_SERVER"),
        keycloak_realm=os.environ.get("KEYCLOAK_REALM"),
        teams_admin_username=os.environ.get("KEYCLOAK_TEAM_ADMIN_USERNAME"),
        teams_admin_password=os.environ.get("KEYCLOAK_TEAM_ADMIN_PASSWORD"),
    ):
        if not keycloak_server_url:
            raise ConfigurationError("keycloak_server_url is not set")
        if not keycloak_realm:
            raise ConfigurationError("keycloak_realm is not set")
        if not teams_admin_username:
            raise ConfigurationError("teams_admin_username is not set")

        self.keycloak_server_url = keycloak_server_url
        self.keycloak_realm = keycloak_realm
        self.teams_admin_username = teams_admin_username

        if teams_admin_password is None:
            teams_admin_password = SsmClient.get_secret(
                "/dataplatform/teams-api/keycloak-teams-admin-password"
            )
        self.teams_admin_password = teams_admin_password

        self.teams_admin_client = KeycloakAdmin(
            server_url=f"{self.keycloak_server_url}/auth/",
            realm_name=self.keycloak_realm,
            username=self.teams_admin_username,
            password=self.teams_admin_password,
            verify=True,
        )

    def list_teams(self, realm_role: Optional[str] = None):
        try:
            groups = (
                self._get_groups_with_realm_role(realm_role)
                if realm_role
                else self.teams_admin_client.get_groups()
            )
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError

        return [group for group in groups if is_team_group(group["name"])]

    def get_team(self, team_id: str):
        try:
            group = self.teams_admin_client.get_group(group_id=team_id)
        except KeycloakGetError:
            raise TeamNotFoundError
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError
        if not is_team_group(group["name"]):
            raise TeamNotFoundError
        return group

    def get_team_members(self, team_id: str):
        team = self.get_team(team_id)
        try:
            members = self.teams_admin_client.get_group_members(group_id=team["id"])
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError
        return members

    def _get_groups_with_realm_role(self, role_name):
        """Return list of groups assigned specified realm role.

        This is similar to `get_client_role_members` (which queries only users, not groups).
        https://github.com/marcospereirampj/python-keycloak/blob/master/keycloak/keycloak_admin.py#L1303
        https://www.keycloak.org/docs-api/15.1/rest-api/index.html#_roles_resource

        Return empty list if role does not exist.
        """
        client_role_group_members_url = (
            URL_ADMIN_REALM_ROLES + "/{role-name}/groups"
        ).format(
            **{
                "realm-name": self.teams_admin_client.realm_name,
                "role-name": role_name,
            }
        )
        try:
            return list(self._get_all_raw(client_role_group_members_url))
        except KeycloakGetError as e:
            if e.response_code == 404:
                return []
            raise

    def _get_all_raw(self, url, params={}):
        """Yield all from paginated results.

        Simplified re-implementation of python-keycloak internal method `__fetch_all`.
        https://github.com/marcospereirampj/python-keycloak/blob/master/keycloak/keycloak_admin.py#L209

        TODO: Could possibly be generalized and reused for resource_server.py::ResourceServer::_get_permissions.
        """
        query_params = {
            **params,
            "max": self.MAX_ITEMS_PER_PAGE,
            "first": 0,
        }

        while True:
            partial_results = raise_error_from_response(
                self.teams_admin_client.raw_get(url, **query_params),
                KeycloakGetError,
            )
            if partial_results:
                for result in partial_results:
                    yield result
                if len(partial_results) < self.MAX_ITEMS_PER_PAGE:
                    return
                query_params["first"] += len(partial_results)
            else:
                return


def log_keycloak_error(keycloak_exception):
    logger.info(f"Keycloak response status code: {keycloak_exception.response_code}")
    logger.info(f"Keycloak response body: {keycloak_exception.response_body}")
    logger.exception(keycloak_exception)

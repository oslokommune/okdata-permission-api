import logging
import os

from keycloak import ConnectionManager, KeycloakAdmin
from keycloak.exceptions import (
    KeycloakError,
    KeycloakGetError,
    KeycloakPutError,
    raise_error_from_response,
)
from keycloak.urls_patterns import URL_ADMIN_REALM_ROLES

from dataplatform_keycloak.exceptions import (
    ConfigurationError,
    TeamNameExistsError,
    TeamNotFoundError,
    TeamsServerError,
    UserNotFoundError,
)
from dataplatform_keycloak.groups import (
    is_team_group,
    team_attribute_to_group_attribute,
    team_name_to_group_name,
)
from dataplatform_keycloak.jwt import generate_jwt
from dataplatform_keycloak.ssm import SsmClient

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


class TeamsKeycloakAdmin(KeycloakAdmin):
    def __init__(self, server_url, admin_api_server_url=None, **kwargs):
        self.admin_api_server_url = admin_api_server_url
        super().__init__(server_url=server_url, **kwargs)

    def get_token(self):
        """Get access token for admin user and configure `ConnectionManager`.

        Overrides `KeycloakAdmin::get_token()` to allow usage of another base url for
        requests towards the Admin API, in this case a configured Kong route that acts
        as a proxy:
        https://github.com/oslokommune/dataplattform/blob/master/dataplattform-internt/arkitektur/utviklerportalen.md#teknisk
        """
        super().get_token()

        if self.admin_api_server_url:
            headers = {
                "Authorization": "Bearer " + generate_jwt(),
                "Keycloak-Authorization": "Bearer " + self.token.get("access_token"),
                "Content-Type": "application/json",
            }
            self.connection = ConnectionManager(
                base_url=self.admin_api_server_url,
                headers=headers,
                verify=self.verify,
            )


class TeamsClient:
    MAX_ITEMS_PER_PAGE = 300

    def __init__(
        self,
        keycloak_server_url=os.environ.get("KEYCLOAK_SERVER"),
        keycloak_admin_api_url=os.environ.get("KEYCLOAK_TEAM_ADMIN_SERVER"),
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

        if teams_admin_password is None:
            teams_admin_password = SsmClient.get_secret(
                "/dataplatform/teams-api/keycloak-teams-admin-password"
            )

        self.teams_admin_client = TeamsKeycloakAdmin(
            server_url=f"{keycloak_server_url}/auth/",
            admin_api_server_url=keycloak_admin_api_url,
            realm_name=keycloak_realm,
            username=teams_admin_username,
            password=teams_admin_password,
            verify=True,
        )

    def list_teams(self, realm_role=None):
        try:
            groups = (
                self._get_groups_with_realm_role(role_name=realm_role)
                if realm_role
                else self.teams_admin_client.get_groups()
            )
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError

        return [group for group in groups if is_team_group(group["name"])]

    def list_user_teams(self, username):
        try:
            user_id = self.teams_admin_client.get_user_id(username)
            user_groups = self.teams_admin_client.get_user_groups(user_id)
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError
        return [group for group in user_groups if is_team_group(group["name"])]

    def get_team(self, team_id, realm_role=None):
        try:
            group = self.teams_admin_client.get_group(group_id=team_id)
        except KeycloakGetError:
            raise TeamNotFoundError
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError
        if realm_role and realm_role not in group["realmRoles"]:
            raise TeamNotFoundError
        if not is_team_group(group["name"]):
            raise TeamNotFoundError
        return group

    def get_team_by_name(self, team_name, realm_role=None):
        group_name = team_name_to_group_name(team_name)

        try:
            group = next(
                group
                for group in self.list_teams(realm_role)
                if group["name"] == group_name
            )
            return self.get_team(group["id"], realm_role)
        except StopIteration:
            raise TeamNotFoundError

    def get_team_members(self, team_id, realm_role=None):
        team = self.get_team(team_id, realm_role=realm_role)
        try:
            members = self.teams_admin_client.get_group_members(group_id=team["id"])
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError
        return members

    def update_team(self, team_id, name, attributes):
        team = self.get_team(team_id)

        if name:
            team["name"] = team_name_to_group_name(name)

        if attributes:
            for team_attr, value in attributes.dict(
                by_alias=True, exclude_unset=True
            ).items():
                group_attr = team_attribute_to_group_attribute(team_attr)

                if value:
                    team["attributes"][group_attr] = value
                elif group_attr in team["attributes"]:
                    del team["attributes"][group_attr]
        try:
            self.teams_admin_client.update_group(team["id"], team)
        except KeycloakPutError as e:
            if e.response_code == 409:
                raise TeamNameExistsError
            log_keycloak_error(e)
            raise TeamsServerError
        except KeycloakError as e:
            log_keycloak_error(e)
            raise TeamsServerError

        return team

    def update_members(self, team_id, user_ids):
        for user_id in user_ids:
            try:
                self.teams_admin_client.get_user(user_id)
            except KeycloakGetError as e:
                if e.response_code == 404:
                    raise UserNotFoundError(f"User with ID {user_id} not found")
                raise TeamsServerError

        current_member_ids = set(
            member["id"] for member in self.get_team_members(team_id)
        )
        target_member_ids = set(user_ids)

        for user_id in target_member_ids.difference(current_member_ids):
            try:
                self.teams_admin_client.group_user_add(user_id, team_id)
            except KeycloakError as e:
                log_keycloak_error(e)
                raise TeamsServerError

        for user_id in current_member_ids.difference(target_member_ids):
            try:
                self.teams_admin_client.group_user_remove(user_id, team_id)
            except KeycloakError as e:
                log_keycloak_error(e)
                raise TeamsServerError

        return self.get_team_members(team_id)

    def _get_groups_with_realm_role(self, role_name):
        """Return list of groups assigned specified realm role.

        This is similar to `get_client_role_members` (which queries only users, not groups).
        https://github.com/marcospereirampj/python-keycloak/blob/master/keycloak/keycloak_admin.py#L1303
        https://www.keycloak.org/docs-api/15.1/rest-api/index.html#_roles_resource

        Return empty list if role does not exist.
        """

        # URL_ADMIN_REALM_ROLES = "admin/realms/{realm-name}/roles"
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

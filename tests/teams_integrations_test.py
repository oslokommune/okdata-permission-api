import unittest

import pytest

from dataplatform_keycloak.groups import group_name_to_team_name
from dataplatform_keycloak.teams_client import TeamsClient
from tests.setup import (
    local_keycloak_config as kc_config,
    populate_local_keycloak,
)
from tests.utils import (
    auth_header,
    get_bearer_token_for_user,
    invalidate_token,
)


class TestTeamsEndpoints:
    @staticmethod
    @pytest.fixture(autouse=True, scope="class")
    def repopualte_keycloak():
        populate_local_keycloak.populate()

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/teams",
            "/teams/abc-123",
            "/teams/abc-123/members",
        ],
    )
    def test_endpoints_auth(self, mock_client, endpoint):
        # No bearer token
        response = mock_client.get(endpoint)
        assert response.status_code == 403
        assert response.json() == {"detail": "Not authenticated"}

        # Invalid token
        invalid_token = invalidate_token(get_bearer_token_for_user(kc_config.janedoe))
        response = mock_client.get(endpoint, headers=auth_header(invalid_token))
        assert response.status_code == 401
        assert response.json() == {"message": "Invalid access token"}

    # GET /teams
    def test_list_teams(self, mock_client):
        response = mock_client.get(
            "/teams",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_teams_filtered_by_role(self, mock_client):
        response = mock_client.get(
            "/teams",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
            params={"has_role": kc_config.internal_team_realm_role},
        )
        assert response.status_code == 200

        unittest.TestCase().assertCountEqual(
            [team["name"] for team in response.json()],
            kc_config.internal_teams,
        )

    # GET /teams/{team_id}
    def test_get_team(self, mock_client):
        team = TeamsClient().list_teams()[0]

        response = mock_client.get(
            f"/teams/{team['id']}",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 200
        assert response.json() == {
            "id": team["id"],
            "name": group_name_to_team_name(team["name"]),
        }

    def test_get_unknown_team(self, mock_client):
        response = mock_client.get(
            "/teams/abc-123",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Team not found"

    def test_get_group_not_team(self, mock_client):
        non_team_group = [
            group
            for group in TeamsClient().teams_admin_client.get_groups()
            if group["name"] == kc_config.nonteamgroup
        ][0]

        response = mock_client.get(
            f"/teams/{non_team_group['id']}",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Team not found"

    # GET /teams/{team_id}/members
    def test_get_team_members(self, mock_client):
        team = TeamsClient().list_teams()[0]

        response = mock_client.get(
            f"/teams/{team['id']}/members",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 200
        team_members = response.json()
        assert len(team_members) == 1
        assert team_members[0].keys() == {"id", "username"}
        assert team_members[0]["username"] == kc_config.user1["username"]

    def test_get_team_members_for_unknown_team(self, mock_client):
        response = mock_client.get(
            "/teams/abc-123/members",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Team not found"

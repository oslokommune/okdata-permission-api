import unittest

import pytest

from dataplatform_keycloak.groups import (
    group_name_to_team_name,
    team_name_to_group_name,
)
from tests.setup import (
    local_keycloak_config as kc_config,
    populate_local_keycloak,
)
from tests.utils import (
    auth_header,
    get_bearer_token_for_user,
    get_keycloak_group_by_name,
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
    @pytest.mark.parametrize(
        "username,expected_team_names",
        [
            (
                user["username"],
                [
                    group_name_to_team_name(team)
                    for team in user["groups"]
                    if team != kc_config.nonteamgroup
                ],
            )
            for user in kc_config.users
        ],
    )
    def test_list_teams(self, mock_client, username, expected_team_names):
        response = mock_client.get(
            "/teams",
            headers=auth_header(get_bearer_token_for_user(username)),
        )
        team_names_from_response = [team["name"] for team in response.json()]

        assert response.status_code == 200
        unittest.TestCase().assertCountEqual(
            team_names_from_response, expected_team_names
        )

    def test_list_teams_filtered_by_role(self, mock_client):
        response = mock_client.get(
            "/teams",
            headers=auth_header(get_bearer_token_for_user(kc_config.user5["username"])),
            params={"has_role": kc_config.internal_team_realm_role},
        )
        team_names_from_response = [team["name"] for team in response.json()]

        assert response.status_code == 200

        unittest.TestCase().assertCountEqual(
            team_names_from_response, [kc_config.team1]
        )

    def test_list_teams_filtered_by_unknown_role(self, mock_client):
        response = mock_client.get(
            "/teams",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
            params={"has_role": "foo"},
        )
        assert response.status_code == 200
        assert response.json() == []

    # GET /teams/{team_id}
    def test_get_team(self, mock_client):
        team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

        response = mock_client.get(
            f"/teams/{team['id']}",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 200
        assert response.json() == {
            "id": team["id"],
            "name": group_name_to_team_name(team["name"]),
        }

    def test_get_team_not_member(self, mock_client):
        team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team2))

        response = mock_client.get(
            f"/teams/{team['id']}",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 403
        assert response.json() == {"message": "Forbidden"}

    def test_get_unknown_team(self, mock_client):
        response = mock_client.get(
            "/teams/abc-123",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Team not found"

    def test_get_group_not_team(self, mock_client):
        non_team_group = get_keycloak_group_by_name(kc_config.nonteamgroup)

        response = mock_client.get(
            f"/teams/{non_team_group['id']}",
            headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Team not found"

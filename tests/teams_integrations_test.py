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
    set_keycloak_group_members,
)


@pytest.fixture(autouse=True, scope="module")
def repopualte_keycloak():
    populate_local_keycloak.populate()


@pytest.mark.parametrize("endpoint", ["/teams", "/teams/abc-123", "/teams/users/foo"])
def test_endpoints_auth(mock_client, endpoint):
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
def test_list_teams(mock_client, username, expected_team_names):
    response = mock_client.get(
        "/teams", headers=auth_header(get_bearer_token_for_user(username))
    )
    team_names_from_response = [team["name"] for team in response.json()]

    assert response.status_code == 200
    unittest.TestCase().assertCountEqual(team_names_from_response, expected_team_names)


def test_list_all_teams(mock_client):
    response = mock_client.get(
        "/teams?include=all",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200
    assert {team["name"] for team in response.json()} == set(kc_config.teams)


def test_list_teams_is_member(mock_client):
    response = mock_client.get(
        "/teams?include=all",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200

    teams = {team["name"]: team for team in response.json()}
    assert teams["team1"]["is_member"]
    assert not teams["team2"]["is_member"]
    assert teams["team3"]["is_member"]


def test_list_teams_filtered_by_role(mock_client):
    response = mock_client.get(
        "/teams",
        headers=auth_header(get_bearer_token_for_user(kc_config.user5["username"])),
        params={"has_role": kc_config.internal_team_realm_role},
    )
    team_names_from_response = [team["name"] for team in response.json()]

    assert response.status_code == 200

    unittest.TestCase().assertCountEqual(team_names_from_response, [kc_config.team1])


def test_list_teams_filtered_by_unknown_role(mock_client):
    response = mock_client.get(
        "/teams",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        params={"has_role": "foo"},
    )
    assert response.status_code == 200
    assert response.json() == []


# GET /teams/{team_id}
def test_get_team(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": group_name_to_team_name(team["name"]),
        "is_member": True,
        "attributes": {"email": [], "slack-url": []},
    }


def test_get_team_non_member(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team2))

    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": group_name_to_team_name(team["name"]),
        "is_member": False,
        "attributes": {"email": [], "slack-url": []},
    }


def test_get_unknown_team(mock_client):
    response = mock_client.get(
        "/teams/abc-123",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Team not found"


def test_get_group_not_team(mock_client):
    non_team_group = get_keycloak_group_by_name(kc_config.nonteamgroup)

    response = mock_client.get(
        f"/teams/{non_team_group['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Team not found"


def test_get_team_with_role(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))
    response = mock_client.get(
        f"/teams/{team['id']}",
        params={"has_role": kc_config.internal_team_realm_role},
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": group_name_to_team_name(team["name"]),
        "is_member": True,
        "attributes": {"email": [], "slack-url": []},
    }


def test_get_team_with_attributes(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team3))
    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": kc_config.team3,
        "is_member": True,
        "attributes": {"email": ["foo@example.org"], "slack-url": []},
    }


def test_get_team_with_non_matching_role(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team2))

    response = mock_client.get(
        f"/teams/{team['id']}",
        params={"has_role": kc_config.internal_team_realm_role},
        headers=auth_header(get_bearer_token_for_user(kc_config.misty)),
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Team not found"


# GET /teams/name/{team_name}
def test_get_team_by_name(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.get(
        f"/teams/name/{kc_config.team1}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": kc_config.team1,
        "is_member": True,
        "attributes": {"email": [], "slack-url": []},
    }


def test_get_team_by_name_non_member(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team2))

    response = mock_client.get(
        f"/teams/name/{kc_config.team2}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": kc_config.team2,
        "is_member": False,
        "attributes": {"email": [], "slack-url": []},
    }


def test_get_team_by_name_with_attributes(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team3))
    response = mock_client.get(
        f"/teams/name/{kc_config.team3}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": team["id"],
        "name": kc_config.team3,
        "is_member": True,
        "attributes": {"email": ["foo@example.org"], "slack-url": []},
    }


def test_get_team_by_name_group_but_not_team(mock_client):
    response = mock_client.get(
        f"/teams/name/{kc_config.nonteamgroup}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 404


def test_get_team_by_name_group_name(mock_client):
    group_name = team_name_to_group_name(kc_config.team1)

    response = mock_client.get(
        f"/teams/name/{group_name}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 404


def test_get_team_by_name_non_existent(mock_client):
    response = mock_client.get(
        "/teams/name/3PAdnssX7suv60xqiQov",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 404


def test_get_team_by_name_unauthenticated(mock_client):
    response = mock_client.get(f"/teams/name/{kc_config.team1}")
    assert response.status_code == 403


# GET /teams/{team_id}/members
def test_get_team_members(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.get(
        f"/teams/{team['id']}/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "username": "janedoe",
            "name": None,
            "email": None,
        },
        {
            "username": "misty",
            "name": "Misty Williams",
            "email": None,
        },
    ]


def test_get_team_members_non_member(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.get(
        f"/teams/{team['id']}/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.homersimpson)),
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "username": "janedoe",
            "name": None,
            "email": None,
        },
        {
            "username": "misty",
            "name": "Misty Williams",
            "email": None,
        },
    ]


def test_get_team_members_non_existent(mock_client):
    response = mock_client.get(
        "/teams/8f8c9efad971e78b8d69/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.homersimpson)),
    )
    assert response.status_code == 404


# PATCH /teams/{team_id}
def test_update_team_rename(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"name": "new-name"},
    )
    assert response.status_code == 200

    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "new-name"

    # Clean up
    mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"name": kc_config.team1},
    )


def test_update_team_rename_conflict(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"name": "team2"},
    )
    assert response.status_code == 409


def test_update_team_attributes(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={
            "attributes": {
                "email": ["foo@bar.org"],
                "slack-url": ["https://foo.slack.com/abc"],
                "unknown-attr": ["foo"],
            }
        },
    )
    assert response.status_code == 200

    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200
    assert response.json()["attributes"] == {
        "email": ["foo@bar.org"],
        "slack-url": ["https://foo.slack.com/abc"],
    }

    response = mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"attributes": {"slack-url": []}},
    )
    assert response.status_code == 200

    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200
    assert response.json()["attributes"] == {
        "email": ["foo@bar.org"],
        "slack-url": [],
    }

    response = mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"attributes": {"email": [], "unknown-attr": []}},
    )
    assert response.status_code == 200

    response = mock_client.get(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200
    assert response.json()["attributes"] == {"email": [], "slack-url": []}


def test_update_team_non_existent(mock_client):
    response = mock_client.patch(
        "/teams/foo",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"name": "foo"},
    )
    assert response.status_code == 404


def test_get_team_members_unauthenticated(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))
    response = mock_client.get(f"/teams/{team['id']}/members")
    assert response.status_code == 403


def test_update_team_unauthenticated(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))
    response = mock_client.patch(f"/teams/{team['id']}", json={"name": "foo"})
    assert response.status_code == 403


def test_update_team_non_member(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team2))

    response = mock_client.patch(
        f"/teams/{team['id']}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json={"name": "foo"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "target_members",
    [
        [],
        [kc_config.homersimpson],
        [kc_config.janedoe, kc_config.misty, kc_config.homersimpson],
        [kc_config.janedoe, kc_config.misty],
        [kc_config.janedoe],
    ],
)
def test_update_team_members(mock_client, target_members):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.put(
        f"/teams/{team['id']}/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json=target_members,
    )
    assert response.status_code == 200
    members_from_response = [member["username"] for member in response.json()]
    unittest.TestCase().assertCountEqual(members_from_response, target_members)

    # Clean up
    set_keycloak_group_members(
        team["id"],
        [
            user["username"]
            for user in kc_config.users
            if team["name"] in user["groups"]
        ],
    )


def test_update_team_members_duplicated_user(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))
    target_members = [kc_config.janedoe, kc_config.misty, kc_config.misty]

    response = mock_client.put(
        f"/teams/{team['id']}/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json=target_members,
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_team_members_non_existent_team(mock_client):
    response = mock_client.put(
        "/teams/foo/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json=[],
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Team not found"


def test_update_team_members_non_existent_user(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))

    response = mock_client.put(
        f"/teams/{team['id']}/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json=["foo"],
    )
    assert response.status_code == 404
    assert response.json()["message"] == "User with username foo not found"


def test_update_team_members_unauthenticated(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team1))
    response = mock_client.put(f"/teams/{team['id']}/members", json=[])
    assert response.status_code == 403


def test_update_team_members_non_member(mock_client):
    team = get_keycloak_group_by_name(team_name_to_group_name(kc_config.team2))

    response = mock_client.put(
        f"/teams/{team['id']}/members",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
        json=[],
    )
    assert response.status_code == 403


def test_get_user_by_username(mock_client):
    response = mock_client.get(
        f"/teams/users/{kc_config.homersimpson}",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 200
    assert response.json() == {
        "username": kc_config.homersimpson,
        "name": None,
        "email": None,
    }


def test_get_user_by_username_non_existent(mock_client):
    response = mock_client.get(
        "/teams/users/foo",
        headers=auth_header(get_bearer_token_for_user(kc_config.janedoe)),
    )
    assert response.status_code == 404
    assert response.json()["message"] == "User not found"

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models import OkdataPermission, Team, TeamMember, UpdatePermissionBody, User
from models.models import TeamAttributes


@pytest.fixture
def uma_permission():
    return {
        "name": "okdata:dataset:foo:read",
        "description": "Allows reading the dataset `foo`.",
        "scopes": ["okdata:dataset:read"],
        "groups": [],
        "users": ["user"],
        "clients": [],
        "logic": "POSITIVE",
        "decisionStrategy": "AFFIRMATIVE",
    }


@patch("models.scope._SCOPES", {"okdata:dataset": ["read"]})
def test_okdata_permission_from_uma_permission(uma_permission):
    p = OkdataPermission.from_uma_permission(uma_permission)
    assert p.resource_name == "okdata:dataset:foo"
    assert p.description == "Allows reading the dataset `foo`."
    assert p.scope == "okdata:dataset:read"
    assert p.teams == []
    assert p.users == ["user"]
    assert p.clients == []


@patch("models.scope._SCOPES", {"okdata:dataset": ["write"]})
def test_okdata_permission_from_uma_permission_unknown_scope(uma_permission):
    with pytest.raises(ValueError):
        OkdataPermission.from_uma_permission(uma_permission)


def test_team_member_name_from_first_and_last_name():
    member = TeamMember.model_validate(
        {
            "username": "janedoe",
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane@example.org",
        }
    )
    assert member.username == "janedoe"
    assert member.name == "Jane Doe"
    assert member.email == "jane@example.org"


def test_team_member_missing_name_and_email():
    member = TeamMember.model_validate({"username": "janedoe"})
    assert member.name is None
    assert member.email is None


def test_team_attributes_populated_by_alias_and_field_name():
    by_alias = TeamAttributes.model_validate(
        {"slack-url": ["https://example.slack.com/abc"]}
    )
    by_field_name = TeamAttributes.model_validate(
        {"slack_url": ["https://example.slack.com/abc"]}
    )
    assert by_alias == by_field_name


def test_team_attributes_dump_json_strings_by_alias():
    # `TeamsClient.update_team` relies on this dump format when writing
    # attributes back to Keycloak: alias keys and plain string values.
    attributes = TeamAttributes.model_validate(
        {"email": ["jane@example.org"], "slack-url": ["https://example.slack.com/abc"]}
    )
    assert attributes.model_dump(mode="json", by_alias=True, exclude_unset=True) == {
        "email": ["jane@example.org"],
        "slack-url": ["https://example.slack.com/abc"],
    }


def test_team_attributes_url_normalization():
    # URLs without a path are normalized with a trailing slash.
    attributes = TeamAttributes.model_validate(
        {"slack-url": ["https://example.slack.com"]}
    )
    assert attributes.model_dump(mode="json", by_alias=True) == {
        "email": [],
        "slack-url": ["https://example.slack.com/"],
    }


@pytest.mark.parametrize(
    "attributes",
    [
        {"email": ["not-an-email"]},
        {"slack-url": ["not-a-url"]},
    ],
)
def test_team_attributes_invalid_values(attributes):
    with pytest.raises(ValidationError):
        TeamAttributes.model_validate(attributes)


def test_team_cleans_name_and_attributes():
    team = Team.model_validate(
        {
            "id": "abc-123",
            "name": "TEAM-foo",
            "is_member": True,
            "attributes": {
                "TEAM-email": ["jane@example.org"],
                "TEAM-slack-url": ["https://example.slack.com/abc"],
                "internal-attr": ["excluded"],
            },
        }
    )
    assert team.name == "foo"
    assert team.attributes.model_dump(mode="json", by_alias=True) == {
        "email": ["jane@example.org"],
        "slack-url": ["https://example.slack.com/abc"],
    }


def test_team_attributes_excluded_when_unset():
    # `GET /teams` relies on unset fields being excluded from the response
    # when `response_model_exclude_unset` is set.
    team = Team.model_validate(
        {"id": "abc-123", "name": "TEAM-foo", "is_member": False}
    )
    assert team.model_dump(exclude_unset=True) == {
        "id": "abc-123",
        "name": "foo",
        "is_member": False,
    }


def test_user_rejects_non_string_user_id():
    # Unlike Pydantic v1, v2 doesn't coerce numbers to strings.
    with pytest.raises(ValidationError):
        User.model_validate({"user_id": 123, "user_type": "user"})


def test_user_rejects_unknown_user_type():
    with pytest.raises(ValidationError):
        User.model_validate({"user_id": "janedoe", "user_type": "gnome"})


@patch("models.scope._SCOPES", {"okdata:dataset": ["read"]})
def test_update_permission_body_accepts_all_scope():
    body = UpdatePermissionBody.model_validate({"scope": "__all__"})
    assert body.scope == "__all__"
    assert body.add_users == []
    assert body.remove_users == []


@patch("models.scope._SCOPES", {"okdata:dataset": ["read"]})
def test_update_permission_body_unknown_scope():
    with pytest.raises(ValidationError):
        UpdatePermissionBody.model_validate({"scope": "okdata:dataset:write"})

import logging
import os
from enum import Enum
from typing import List, Union

from pydantic import BaseModel, EmailStr, Field, HttpUrl, root_validator, validator

from dataplatform_keycloak.groups import (
    group_attribute_to_team_attribute,
    group_name_to_team_name,
    is_team_attribute,
)
from models.scope import all_scopes, all_scopes_for_type
from resources.resource_util import (
    resource_name_from_permission_name,
    resource_type_from_resource_name,
)

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


class UserType(str, Enum):
    GROUP = "team"
    USER = "user"
    CLIENT = "client"


class User(BaseModel):
    user_id: str
    user_type: UserType


class TeamMember(BaseModel):
    username: str
    name: Union[str, None]
    email: Union[str, None]

    @root_validator(pre=True)
    def check_values(cls, values):
        values["name"] = (
            " ".join(
                [
                    values.get("firstName", ""),
                    values.get("lastName", ""),
                ]
            ).strip()
            or None
        )
        return values

    class Config:
        allow_population_by_field_name = True


class TeamAttributes(BaseModel):
    email: List[EmailStr] = []
    slack_url: List[HttpUrl] = Field([], alias="slack-url")

    class Config:
        allow_population_by_field_name = True


class Team(BaseModel):
    id: str
    name: str
    is_member: bool
    attributes: Union[TeamAttributes, None] = None

    @validator("name", pre=True)
    def clean_name(cls, v):
        return group_name_to_team_name(v)

    @validator("attributes", pre=True)
    def clean_attributes(cls, v):
        return {
            group_attribute_to_team_attribute(key): value
            for key, value in v.items()
            if is_team_attribute(key)
        }


class UpdateTeamBody(BaseModel):
    name: Union[str, None] = None
    attributes: Union[TeamAttributes, None] = None


class CreateResourceBody(BaseModel):
    owner: User
    resource_name: str

    @validator("resource_name")
    def check_resource_name(cls, resource_name):
        # Raises `ValueError` when the resource type is unknown.
        all_scopes_for_type(resource_type_from_resource_name(resource_name))
        return resource_name


class OkdataPermission(BaseModel):
    resource_name: str
    description: str
    scope: str
    teams: List[str]
    users: List[str]
    clients: List[str]

    @validator("scope")
    def check_scope(cls, scope):
        known_scopes = all_scopes()
        if scope not in known_scopes:
            raise ValueError(
                "Unknown scope: {}. Must be one of: {}".format(scope, known_scopes)
            )
        return scope

    @staticmethod
    def from_uma_permission(uma_permission: dict):
        scope, *extra_scopes = uma_permission["scopes"]

        if extra_scopes:
            logger.warning(f"Got unexpcted additional scopes: {extra_scopes}")

        return OkdataPermission(
            resource_name=resource_name_from_permission_name(uma_permission["name"]),
            description=uma_permission["description"],
            scope=scope,
            teams=[
                group_name_to_team_name(group[1:])
                for group in uma_permission.get("groups", [])
            ],
            users=uma_permission.get("users", []),
            clients=uma_permission.get("clients", []),
        )


class UpdatePermissionBody(BaseModel):
    add_users: List[User] = []
    remove_users: List[User] = []
    scope: str


class MyPermissionsScopes(BaseModel):
    scopes: list[str]

import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Union
from uuid import UUID

from pydantic import BaseModel, validator

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


class Team(BaseModel):
    id: str
    name: str
    attributes: Union[dict, None] = None

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


class MyPermissionsResponse(BaseModel):
    class MyPermissionScopes(BaseModel):
        scopes: List[str]

    __root__: Dict[str, MyPermissionScopes]


class WebhookTokenAuthResponse(BaseModel):
    access: bool
    reason: str = None


class WebhookTokenOperation(Enum):
    READ = "read"
    WRITE = "write"


class CreateWebhookTokenBody(BaseModel):
    operation: WebhookTokenOperation


class WebhookTokenItem(BaseModel):
    token: UUID
    created_by: str
    dataset_id: str
    operation: WebhookTokenOperation
    created_at: datetime
    expires_at: datetime
    is_active: bool = True

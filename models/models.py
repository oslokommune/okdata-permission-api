from enum import Enum
from typing import List

from pydantic import BaseModel, validator

from models.scope import all_scopes


class UserType(str, Enum):
    GROUP = "team"
    USER = "user"
    CLIENT = "client"


class User(BaseModel):
    user_id: str
    user_type: UserType


class CreateResourceBody(BaseModel):
    owner: User


class OkdataPermission(BaseModel):
    resource_name: str
    description: str
    scopes: List[str]
    teams: List[str]
    users: List[str]
    clients: List[str]

    @validator("scopes", each_item=True)
    def check_scopes(cls, scope):
        known_scopes = all_scopes()
        if scope not in known_scopes:
            raise ValueError(
                "Unknown scope: {}. Must be one of: {}".format(scope, known_scopes)
            )
        return scope

    @staticmethod
    def from_uma_permission(uma_permission: dict):
        return OkdataPermission(
            resource_name=":".join(uma_permission["name"].split(":")[:3]),
            description=uma_permission["description"],
            scopes=uma_permission["scopes"],
            teams=[group[1:] for group in uma_permission.get("groups", [])],
            users=uma_permission.get("users", []),
            clients=uma_permission.get("clients", []),
        )


class UpdatePermissionBody(BaseModel):
    add_users: List[User] = []
    remove_users: List[User] = []
    scope: str

from pydantic import BaseModel
from enum import Enum
from typing import List


class ResourceScope(Enum):
    read = "okdata:dataset:read"
    write = "okdata:dataset:write"
    update = "okdata:dataset:update"
    owner = "okdata:dataset:owner"

    @staticmethod
    def list_values():
        return list(map(lambda rs: rs.value, ResourceScope))


class UserType(Enum):
    GROUP = "team"
    USER = "user"
    CLIENT = "client"


class User(BaseModel):
    user_id: str
    user_type: UserType


class CreateResourceBody(BaseModel):
    dataset_id: str
    owner: User


class OkdataPermission(BaseModel):
    dataset_id: str
    description: str
    scopes: List[str]
    teams: List[str]
    users: List[str]
    clients: List[str]

    @staticmethod
    def from_uma_permission(uma_permission: dict):
        return OkdataPermission(
            dataset_id=uma_permission["name"].split(":")[0],
            description=uma_permission["description"],
            scopes=uma_permission["scopes"],
            teams=[group[1:] for group in uma_permission.get("groups", [])],
            users=uma_permission.get("users", []),
            clients=uma_permission.get("clients", []),
        )


class UpdatePermissionBody(BaseModel):
    add_users: List[User] = []
    remove_users: List[User] = []
    scope: ResourceScope

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


class OwnerType(Enum):
    GROUP = "team"
    USER = "user"
    CLIENT = "client"


class CreateResourceBody(BaseModel):
    dataset_id: str
    owner_id: str
    owner_type: OwnerType


class OkdataPermission(BaseModel):
    dataset_id: str
    description: str
    scopes: List[str]
    teams: List[str]
    users: List[str]
    clients: List[str]

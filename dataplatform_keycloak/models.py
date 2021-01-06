from enum import Enum


class ResourceScope(Enum):
    read = "okdata:dataset:read"
    write = "okdata:dataset:write"
    update = "okdata:dataset:update"
    owner = "okdata:dataset:owner"

    @staticmethod
    def list_values():
        return list(map(lambda rs: rs.value, ResourceScope))

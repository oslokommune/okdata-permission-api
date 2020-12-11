from enum import Enum


class ResourceScope(Enum):
    read = "ok:origo:dataset:read"
    write = "ok:origo:dataset:write"
    update = "ok:origo:dataset:update"
    owner = "ok:origo:dataset:owner"

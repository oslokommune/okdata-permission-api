class ResourceNotFoundException(Exception):
    pass


class PermissionNotFoundException(Exception):
    pass


class CannotRemoveOnlyAdminException(Exception):
    pass


class ConfigurationError(Exception):
    pass


class TeamsServerError(Exception):
    pass


class TeamNotFoundError(Exception):
    pass

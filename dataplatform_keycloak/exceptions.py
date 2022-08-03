class ResourceNotFoundError(Exception):
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


class UserNotFoundError(Exception):
    pass


class UserAlreadyTeamMemberError(Exception):
    pass


class UserNotTeamMemberError(Exception):
    pass

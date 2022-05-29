"""Our own Exception classes."""


class NextCloudTalkException(Exception):
    """Generic Exception."""

    pass


class NextCloudTalkBadRequest(NextCloudTalkException):
    """400 - User made a bad request."""

    pass


class NextCloudTalkUnauthorized(NextCloudTalkException):
    """401 - User account is not authorized."""

    pass


class NextCloudTalkForbidden(NextCloudTalkException):
    """403 - Forbidden action due to permissions."""

    pass


class NextCloudTalkNotFound(NextCloudTalkException):
    """404 - Object was not found."""

    pass


class NextCloudTalkConflict(NextCloudTalkException):
    """409 - Conflict - user has duplicate sessions."""

    pass


class NextCloudTalkPreconditionFailed(NextCloudTalkException):
    """412 - User tried to join chat room without going to lobby."""

    pass


class NextCloudTalkNotCapable(NextCloudTalkException):
    """Raised when server does not have required capability."""

    pass

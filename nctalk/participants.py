"""Objects representing conversation participants."""
from enum import IntFlag, Enum


class Permissions(IntFlag):
    """Enumeration for conversation permissions."""

    default = 0
    custom = 1
    start_call = 2
    join_call = 4
    can_ignore_lobby = 8
    can_publish_audio = 16
    can_publish_video = 32
    can_publish_screen_sharing = 64


class Participant(object):
    """Interact with conversation participants."""

    def __init__(self, data: dict):
        self.__dict__.update(data)

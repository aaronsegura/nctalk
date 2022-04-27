"""Conversation API."""

import xmltodict

from typing import Union
from collections import OrderedDict
from enum import IntFlag, Enum

from nextcloud import NextCloud

from nctalk.api import NextCloudTalkAPI, NextCloudTalkException


class ConversationType(Enum):
    """Conversation Types."""

    one_to_one = 1
    group = 2
    public = 3
    changelog = 4


class NotificationLevel(Enum):
    """Notification Levels."""

    default = 0
    always_notify = 1
    notify_on_mention = 2
    never_notify = 3


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


class ConversationException(Exception):
    """Our own little exception class."""

    pass


class Conversation(object):
    """Represents a NextCloud Talk Conversation.

    Conversation dictionary:
    https://nextcloud-talk.readthedocs.io/en/latest/conversation/#get-user-s-conversations
    """

    def __init__(self, data: dict, conversation_api: 'ConversationAPI'):
        """Initialize object with data from  API."""
        self.__dict__.update(data)
        self.api = conversation_api

    def __repr__(self):
        """Return representation of object."""
        return '{}({})'.format(self.__class__.__name__, self.__dict__)

    def __str__(self):
        """Return user-readable object string."""
        return 'Conversation({token}, {type}, {displayName})'.format(**self.__dict__)

    def rename(self, room_name: str):
        """Rename the room.

        Method: PUT
        Endpoint: /room/{token}
        Data:

        field     type    Description
        roomName  string  New name for the conversation (1-200 characters)

        Response:
        Status code:
        200 OK
        400 Bad Request When the name is too long or empty
        400 Bad Request When the conversation is a one to one conversation
        403 Forbidden When the current user is not a moderator/owner
        404 Not Found When the conversation could not be found for the
            participant
        """
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}',
            data={'roomName': room_name})

    def delete(self):
        """Delete the room.

        Method: DELETE
        Endpoint: /room/{token}

        Response:

        Status code:
        200 OK
        400 Bad Request When the conversation is a one-to-one conversation
            (Use Remove yourself from a conversation instead)
        403 Forbidden When the current user is not a moderator/owner
        404 Not Found When the conversation could not be found for the
            participant
        """
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}')

    def set_description(self, description: str):
        """Set description on room.

        Required capability: room-description
        Method: PUT
        Endpoint: /room/{token}/description
        Data:

        field       type    Description
        description string  New description for the conversation

        Response:
        Status code:
        200 OK
        400 Bad Request When the description is too long
        400 Bad Request When the conversation is a one to one conversation
        403 Forbidden When the current user is not a moderator/owner
        404 Not Found When the conversation could not be found for the participant
        """
        req = self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/description',
            data={'description': description})

        self.description = description

    def allow_guests(self, allow_guests: bool):
        """Allow guests in a conversation."""
        if allow_guests:
            self.api.query(
                method='POST',
                sub=f'/room/{self.token}/public')
        else:
            self.api.query(
                method='DELETE',
                sub=f'/room/{self.token}/public')

    def read_only(self, read_only: int):
        """Set conversation to read-only or read-write."""
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/read-only',
            data={'state': read_only})

    def set_password(self, password: str):
        """Set password for this converstaion."""
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/password',
            data={'password': password})

    def add_to_favorites(self):
        """Add this room to favorites."""
        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/favorite')

    def remove_from_favorites(self):
        """Remove this room from favorites."""
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}/favorites')

    def set_notification_level(self, notification_level: Union[int, str]):
        """Set notification level for room.

        See NOTIFICATION_LEVEL constants above.
        """
        if notification_level is str:
            notification_level = NotificationLevel.notification_level

        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/notify',
            data={'level': notification_level})

    def leave(self):
        """Leave this room."""
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}/participants/self')

    def participants(self, include_status: bool = False):
        """Return list of participants."""
        return self.api.query(
            sub=f'/room/{self.token}/participants',
            data={'includeStatus': include_status})


class ConversationAPI(NextCloudTalkAPI):
    """Interface to the Conversations API.

    https://nextcloud-talk.readthedocs.io/en/latest/conversation/
    """

    def __init__(self, nextcloud_client: NextCloud):
        """Initialize the Conversation API."""
        self.api_endpoint = '/ocs/v2.php/apps/spreed/api/v4'
        super().__init__(nextcloud_client, api_endpoint=self.api_endpoint)

    def list(
            self,
            no_status_update: int = 0,
            include_status: bool = False) -> list:
        """Return list of user's conversations.

        Method: GET
        Endpoint: /room
        Data:

        field           type Description
        noStatusUpdate  int  Whether the "online" user status of the current
                             user should be "kept-alive" (1) or not (0)
                             (defaults to 0)
        includeStatus   bool Whether the user status information of all
                             one-to-one conversations should be loaded
                             (default false)
        Response:
        Status code:

        200 OK
        401 Unauthorized when the user is not logged in

        https://nextcloud-talk.readthedocs.io/en/latest/conversation/
        """
        data = {
            'noStatusUpdate': no_status_update,
            'includeStatus': include_status,
        }
        request = self.query(sub='/room', data=data)

        if not request:  # Zero results
            rooms = []
        elif type(request['element']) == OrderedDict:  # One Result
            rooms = [Conversation(request['element'], self)]
        else:  # Multiple Results
            rooms = [
                Conversation(x, self)
                for x in request['element']
            ]

        return rooms

    def new(
            self,
            room_type: Union[int, str],
            invite: str = '',
            room_name: str = '',
            source: str = '') -> Conversation:
        """Create a new conversation."""
        if type(room_type) is str:
            room_type = ConversationType[room_type].value

        data = {
            'roomType': room_type,
            'invite': invite,
            'source': source,
            'roomName': room_name
        }
        new_room_data = self.query(sub='/room', method="POST", data=data)
        return Conversation(new_room_data, self)

    def get(self, room_token: str) -> Conversation:
        """Get a specific conversation.

        Method: GET
        Endpoint: /room/{token}

        Response:

        Status code:

        200 OK
        404 Not Found When the conversation could not be found for the
            participant
        """
        room_data = self.query(sub=f'/room/{room_token}')
        return Conversation(room_data, self)

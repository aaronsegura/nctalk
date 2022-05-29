"""Conversations API."""

from typing import Union, List

from nextcloud import NextCloud
from urllib3 import HTTPResponse

from nctalk.constants import ConversationType, NotificationLevel, ListableScope, Permissions
from nctalk.api import NextCloudTalkAPI, NextCloudTalkException
from nctalk.participants import Participant
from nctalk.chats import Chat, ChatAPI


class Conversation(object):
    """A NextCloud Talk Conversation.

    Conversation dictionary:
    https://nextcloud-talk.readthedocs.io/en/latest/conversation/#get-user-s-conversations
    """

    def __init__(self, data: dict, conversation_api: 'ConversationAPI'):
        self.__dict__.update(data)
        self.api = conversation_api

        # Conversations and Chats are two different things
        # according to the API /shrug, so generate a Chat()
        # for every Conversation()
        self.chat_api = ChatAPI(self.api.client)
        self.chat = Chat(self.token, self.chat_api)  # type: ignore

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'{self.__class__.__name__}({self.token}, ' \
               f'{ConversationType(int(self.type)).name}, {self.displayName})'  # type: ignore

    def rename(self, room_name: str):
        """Rename the room.

        Method: PUT
        Endpoint: /room/{token}

        field     type    Description
        roomName  string  New name for the conversation (1-200 characters)

        Exceptions:
        400 Bad Request When the name is too long or empty
        400 Bad Request When the conversation is a one to one conversation
        403 Forbidden When the current user is not a moderator/owner
        404 Not Found When the conversation could not be found for the
            participant
        """
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}',  # type: ignore
            data={'roomName': room_name})

    def delete(self):
        """Delete the room.

        Method: DELETE
        Endpoint: /room/{token}

        Exceptions:
        400 Bad Request When the conversation is a one-to-one conversation
            (Use Remove yourself from a conversation instead)
        403 Forbidden When the current user is not a moderator/owner
        404 Not Found When the conversation could not be found for the
            participant
        """
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}')  # type: ignore

    def set_description(self, description: str) -> HTTPResponse:
        """Set description on room.

        Required capability: room-description
        Method: PUT
        Endpoint: /room/{token}/description

        field       type    Description
        description string  New description for the conversation

        Exceptions:
        400 Bad Request When the description is too long
        400 Bad Request When the conversation is a one to one conversation
        403 Forbidden When the current user is not a moderator/owner
        404 Not Found When the conversation could not be found for the participant
        """
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/description',  # type: ignore
            data={'description': description})

        self.description = description

    def allow_guests(self, allow_guests: bool):
        """Allow guests in a conversation."""
        if allow_guests:
            self.api.query(
                method='POST',
                sub=f'/room/{self.token}/public')  # type: ignore
        else:
            self.api.query(
                method='DELETE',
                sub=f'/room/{self.token}/public')  # type: ignore

    def read_only(self, read_only: int):
        """Set conversation to read-only or read-write."""
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/read-only',  # type: ignore
            data={'state': read_only})

    def set_password(self, password: str):
        """Set password for this converstaion."""
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/password',  # type: ignore
            data={'password': password})

    def add_to_favorites(self):
        """Add this room to favorites."""
        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/favorite')  # type: ignore

    def remove_from_favorites(self):
        """Remove this room from favorites."""
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}/favorites')  # type: ignore

    def set_notification_level(self, notification_level: str) -> HTTPResponse:
        """Set notification level for room.

        See constants.NotificationLevel
        """
        data = {
            'level':  NotificationLevel[notification_level].value
        }
        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/notify',  # type: ignore
            data=data)

    def set_call_notification_level(self, notification_level: str) -> HTTPResponse:
        """Set notification level for calls.

        Required capability: notification-calls
        Method: POST
        Endpoint: /room/{token}/notify-calls

        level	int	The call notification level (See Participant call notification levels)

        Exceptions:
        400 Bad Request When the given level is invalid
        401 Unauthorized When the participant is a guest
        404 Not Found When the conversation could not be found for the participant
        """
        data = {
            'level':  NotificationLevel[notification_level].value
        }
        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/notify-calls',  # type: ignore
            data=data)

    def set_permissions(
            self,
            scope: str = 'default',
            permissions: Permissions = Permissions(0)) -> HTTPResponse:
        """Set default or call permissions.

        Method: PUT
        Endpoint: /room/{token}/permissions/{mode}

        mode	string	'default' or 'call', in case of call the permissions will be
                        reset to 0 (default) after the end of a call.
        permissions	int	New permissions for the attendees, see constants list. If
                        permissions are not 0 (default), the 1 (custom) permission
                        will always be added. Note that this will reset all custom
                        permissions that have been given to attendees so far.
        Exceptions:
        400 Bad Request When the conversation type does not support setting publishing
            permissions, e.g. one-to-one conversations
        400 Bad Request When the mode is invalid
        403 Forbidden When the current user is not a moderator, owner or guest moderator
        404 Not Found When the conversation could not be found for the participant
        """
        data = {
            'mode': scope,
            'permissions': permissions,
        }
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/permissions/{scope}',  # type: ignore
            data=data
        )

    def leave(self):
        """Leave this room."""
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}/participants/self')  # type: ignore

    def invite(self, invitee: str, source: str = 'users') -> Union[int, None]:
        """Invite a user to this room.

        Method: POST
        Endpoint: /room/{token}/participants

        newParticipant	string	User, group, email or circle to add
        source	        string	Source of the participant(s) as
                                returned by the autocomplete suggestion
                                endpoint (default is users)
        Exceptions:
        400 Bad Request
            When the source type is unknown, currently users, groups, emails
            are supported. circles are supported with circles-support capability
        400 Bad Request
            When the conversation is a one-to-one conversation or a conversation
            to request a password for a share
        403 Forbidden - When the current user is not a moderator or owner
        404 Not Found - When the conversation could not be found for the participant
        404 Not Found - When the user or group to add could not be found

        Returns:
        type	int     In case the conversation type changed, the new value is
                        returned
        """
        return self.api.query(
            sub=f'/room/{self.token}/participants',  # type: ignore
            data={'newParticipant': invitee, 'source': source})

    @property
    def participants(self, include_status: bool = False) -> List[Participant]:
        """Return list of participants."""
        participants = self.api.query(
            sub=f'/room/{self.token}/participants',  # type: ignore
            data={'includeStatus': include_status})

        result = participants['element']
        if isinstance(result, dict):
            ret = [Participant(result)]
        elif isinstance(result, list):
            ret = [Participant(user) for user in result]
        else:
            raise NextCloudTalkException(
                f'Unknown Return type for participants: {type(result)}')

        return ret

    def send(self, **kwargs):
        """Send a message to a conversation."""
        return self.chat.send(**kwargs)

    def change_listing_scope(self, scope: str) -> None:
        """Change scope for conversation.

        Change who can see the conversation.
        See ListableScope, above.
        """
        self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/listable',  # type: ignore
            data={'scope': ListableScope[scope].value})


class ConversationAPI(NextCloudTalkAPI):
    """Interface to the Conversations API.

    https://nextcloud-talk.readthedocs.io/en/latest/conversation/
    """

    def __init__(self, client: NextCloud):
        self.client = client

        if 'conversation-v4' in self.client.capabilities:  # type: ignore
            self.api_endpoint = '/ocs/v2.php/apps/spreed/api/v4'

        super().__init__(client, api_endpoint=self.api_endpoint)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.client})'

    def __str__(self) -> str:
        return f'{self.__class__.__name__}()'

    def list(
            self,
            no_status_update: int = 0,
            include_status: bool = False) -> List[Conversation]:
        """Return list of user's conversations.

        Method: GET
        Endpoint: /room

        field           type Description
        noStatusUpdate  int  Whether the "online" user status of the current
                             user should be "kept-alive" (1) or not (0)
                             (defaults to 0)
        includeStatus   bool Whether the user status information of all
                             one-to-one conversations should be loaded
                             (default false)
        Exceptions:
        401 Unauthorized when the user is not logged in
        """
        data = {
            'noStatusUpdate': no_status_update,
            'includeStatus': include_status,
        }
        request = self.query(sub='/room', data=data)

        if not request:  # Zero results
            rooms = []
        elif isinstance(request['element'], dict):  # One Result
            rooms = [Conversation(request['element'], self)]
        elif isinstance(request['element'], list):  # Multiple Results
            rooms = [Conversation(x, self) for x in request['element']]
        else:
            raise NextCloudTalkException(f'Unexpected result: {request["element"]}')

        return rooms

    def new(
            self,
            room_type: str,
            invite: str = '',
            room_name: str = '',
            source: str = '') -> Conversation:
        """Create a new conversation."""
        data = {
            'roomType': ConversationType[room_type].value,
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

    def open_conversation_list(self) -> List[Conversation]:
        """Get list of open rooms."""
        request = self.query(sub='/listed-room')

        if not request:  # Zero results
            rooms = []
        elif isinstance(request['element'], dict):  # One Result
            rooms = [Conversation(request['element'], self)]
        elif isinstance(request['element'], list):  # Multiple Results
            rooms = [Conversation(x, self) for x in request['element']]
        else:
            raise NextCloudTalkException(f"Unknown result: {request}")

        return rooms

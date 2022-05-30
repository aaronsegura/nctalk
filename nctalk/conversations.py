"""Conversations API."""

from typing import Union, List

from nextcloud import NextCloud
from urllib3 import HTTPResponse

from nctalk.constants import ConversationType, NotificationLevel, ListableScope, Permissions
from nctalk.api import NextCloudTalkAPI
from nctalk.chats import Chat, ChatAPI
from nctalk.exceptions import NextCloudTalkException, NextCloudTalkNotCapable


class Conversation(object):
    """A NextCloud Talk Conversation.

    https://nextcloud-talk.readthedocs.io/en/latest/conversation/
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
        string = [f'{self.__class__.__name__}({self.token}, ']  # type: ignore
        string.append(f'{ConversationType(int(self.type)).name}, ')  # type: ignore
        string.append(f'{self.displayName})')  # type: ignore
        return " ".join(string)

    def rename(self, room_name: str):
        """Rename the room.

        Method: PUT
        Endpoint: /room/{token}

        #### Arguments:
        roomName  [string]  New name for the conversation (1-200 characters)

        #### Exceptions:
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

    def delete(self) -> HTTPResponse:
        """Delete the room.

        Method: DELETE
        Endpoint: /room/{token}

        #### Exceptions:
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

        #### Arguments:
        description [string] New description for the conversation

        #### Exceptions:
        400 Bad Request When the description is too long

        400 Bad Request When the conversation is a one to one conversation

        403 Forbidden When the current user is not a moderator/owner

        404 Not Found When the conversation could not be found for the participant

        NextCloudTalkNotCapable When server is lacking required capability
        """
        if 'room-description' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable('Server does not support setting room descriptions')

        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/description',  # type: ignore
            data={'description': description})

        self.description = description

    def allow_guests(self, allow_guests: bool):
        """Allow guests in a conversation (public conversation)#
        Method: POST or DELETE
        Endpoint: /room/{token}/public

        #### Arguments:
        allow_guests [bool] Allow (True) or disallow (False) guests

        #### Exceptions:
        400 Bad Request When the conversation is not a group conversation

        403 Forbidden When the current user is not a moderator/owner

        404 Not Found When the conversation could not be found for the participant
        """
        if allow_guests:
            self.api.query(
                method='POST',
                sub=f'/room/{self.token}/public')  # type: ignore
        else:
            self.api.query(
                method='DELETE',
                sub=f'/room/{self.token}/public')  # type: ignore

    def read_only(self, state: int):
        """Set read-only for a conversation

        Required capability: read-only-rooms
        Method: PUT
        Endpoint: /room/{token}/read-only

        #### Arguments:
        state	[int]	New state for the conversation, see constants list

        #### Exceptions:
        400 Bad Request When the conversation type does not support read-only
            (only group and public conversation)

        403 Forbidden When the current user is not a moderator/owner or the
            conversation is not a public conversation

        404 Not Found When the conversation could not be found for the
            participant

        NextCloudTalkNotCapable When server is lacking required capability
        """
        if 'read-only-rooms' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable('Server doesn\'t support read-only rooms.')

        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/read-only',  # type: ignore
            data={'state': state})

    def set_password(self, password: str):
        """Set password for a conversation

        Method: PUT
        Endpoint: /room/{token}/password

        #### Arguments:
        password	string	New password for the conversation

        #### Exceptions
        403 Forbidden When the current user is not a moderator or owner

        403 Forbidden When the conversation is not a public conversation

        404 Not Found When the conversation could not be found for the participant
        """
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.token}/password',  # type: ignore
            data={'password': password})

    def add_to_favorites(self):
        """Add conversation to favorites

        Required capability: favorites
        Method: POST
        Endpoint: /room/{token}/favorite

        #### Exceptions:
        401 Unauthorized When the participant is a guest

        404 Not Found When the conversation could not be found for the participant

        NextCloudTalkNotCapable When server is lacking required capability
        """
        if 'favorites' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable('Server does not support user favorites.')

        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/favorite')  # type: ignore

    def remove_from_favorites(self):
        """Remove conversation from favorites

        Required capability: favorites
        Method: DELETE
        Endpoint: /room/{token}/favorite

        #### Exceptions:
        401 Unauthorized When the participant is a guest

        404 Not Found When the conversation could not be found for the participant

        NextCloudTalkNotCapable When server is lacking required capability
        """
        if 'favorites' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable('Server does not support user favorites.')

        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}/favorites')  # type: ignore

    def set_notification_level(self, notification_level: str) -> HTTPResponse:
        """Set notification level

        Required capability: notification-levels
        Method: POST
        Endpoint: /room/{token}/notify

        #### Arguments:
        notification_level	[str]	The notification level (See constants)

        #### Exceptions:
        400 Bad Request When the given level is invalid

        401 Unauthorized When the participant is a guest

        404 Not Found When the conversation could not be found for the participant
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

        #### Arguments:
        level [int]	The call notification level (See constants)

        #### Exceptions:
        400 Bad Request When the given level is invalid

        401 Unauthorized When the participant is a guest

        404 Not Found When the conversation could not be found for the participant

        NextCloudTalkNotCapable When server is lacking required capability
        """
        if 'notification-calls' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable(
                    'Server does not support setting call notification levels.')

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

        #### Arguments:
        mode [string]	'default' or 'call', in case of call the permissions will be
            reset to 0 (default) after the end of a call.

        permissions	[int] New permissions for the attendees, see constants list. If
            permissions are not 0 (default), the 1 (custom) permission
            will always be added. Note that this will reset all custom
            permissions that have been given to attendees so far.

        #### Exceptions:

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

    def join(
            self,
            password: Union[str, None],
            force: bool = True) -> HTTPResponse:
        """Join a conversation (available for call and chat)

        Method: POST
        Endpoint: /room/{token}/participants/active

        #### Arguments:
        password	[string]	Optional: Password is only required for users
        which are self joined or guests and only when the conversation has
        hasPassword set to true.

        force   [bool]  If set to false and the user has an active
        session already a 409 Conflict will be returned (Default: true - to
        keep the old behaviour)

        #### Exceptions:

        * 403 Forbidden When the password is required and didn't match

        * 404 Not Found When the conversation could not be found for the participant

        * 409 Conflict When the user already has an active Talk session in the conversation
            with this Nextcloud session. The suggested behaviour is to ask the
            user whether they want to kill the old session and force join unless
            the last ping is older than 60 seconds or older than 40 seconds when
            the conflicting session is not marked as in a call.

        #### Data in case of 409 Conflict:

        sessionId   [string]  512 character long session string

        inCall	    [int]   Flags whether the conflicting session is in a potential call

        lastPing	[int]   Timestamp of the last ping of the conflicting session
        """
        data = {
            'password': password,
            'force': force,
        }
        return self.api.query(
            method='POST',
            sub=f'/room/{self.token}/participants/active',  # type: ignore
            data=data)

    def leave(self):
        """Remove yourself from a conversation.

        Method: DELETE
        Endpoint: /room/{token}/participants/self

        #### Exceptions:
        400 Bad Request When the participant is a moderator or owner and there are
            no other moderators or owners left.

        404 Not Found When the conversation could not be found for the participant
        """
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.token}/participants/self')  # type: ignore

    def invite(self, invitee: str, source: str = 'users') -> Union[int, None]:
        """Invite a user to this room.

        Method: POST
        Endpoint: /room/{token}/participants

        #### Arguments:
        invitee	[string]	User, group, email or circle to add

        source  [string]	Source of the participant(s) as
            returned by the autocomplete suggestion endpoint (default is 'users')

        #### Exceptions:
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
        type	[int]   In case the conversation type changed, the new value is
                        returned
        """
        return self.api.query(
            sub=f'/room/{self.token}/participants',  # type: ignore
            data={'newParticipant': invitee, 'source': source})

    @property
    def participants(self, include_status: bool = False) -> List['Participant']:
        """Return list of participants."""
        participants = self.api.query(
            sub=f'/room/{self.token}/participants',  # type: ignore
            data={'includeStatus': include_status})

        result = participants['element']
        if isinstance(result, dict):
            ret = [Participant(result, room=self)]
        elif isinstance(result, list):
            ret = [Participant(user, room=self) for user in result]
        else:
            raise NextCloudTalkException(
                f'Unknown Return type for participants: {type(result)}')

        return ret

    def send(self, **kwargs):
        """Sending a new chat message

        Method: POST
        Endpoint: /chat/{token}
        Data:

        #### Arguments:
        message	[string]	The message the user wants to say

        actorDisplayName	[string]	Guest display name (ignored for logged in users)

        replyTo	[int]	The message ID this message is a reply to (only allowed for
                        messages from the same conversation and when the message type
                        is not system or command)

        referenceId	[string]	A reference string to be able to identify the message
                                again in a "get messages" request, should be a random
                                sha256 (only available with chat-reference-id capability)

        silent	[bool]	If sent silent the message will not create chat notifications
                        even for mentions (only available with silent-send capability)

        #### Exceptions:
        400 Bad Request In case of any other error

        403 Forbidden When the conversation is read-only

        404 Not Found When the conversation could not be found for the participant

        412 Precondition Failed When the lobby is active and the user is not a moderator

        413 Payload Too Large When the message was longer than the allowed limit of 32000
            characters (or 1000 until Nextcloud 16.0.1, check the spreed => config => chat
            => max-length capability for the limit)

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that has
                                        read privacy set to public. When the user themself
                                        has it set to private the value the header is not
                                        set (only available with chat-read-status capability)
        """
        return self.chat.send(**kwargs)

    def change_listing_scope(self, scope: str) -> None:
        """Change scope for conversation.

        Change who can see the conversation.
        See ListableScope, above.

        Required capability: listable-rooms
        Method: PUT
        Endpoint: /room/{token}/listable

        #### Arguments:
        scope	[str]	New flags for the conversation (see constants)
        Response:

        #### Exceptions:
        400 Bad Request When the conversation type does not support making it listable
            (only group and public conversation)

        403 Forbidden When the current user is not a moderator/owner or the conversation
            is not a public conversation

        404 Not Found When the conversation could not be found for the participant

        NextCloudTalkNotCapable When server is lacking required capability
        """
        if 'listable-rooms' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable('Server does not support listable rooms.')

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
        else:
            raise NextCloudTalkException('Unable to determine active Conversation endpoint.')

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

        #### Arguments:
        noStatusUpdate  [int]  Whether the "online" user status of the current
                             user should be "kept-alive" (1) or not (0)
                             (defaults to 0)
        includeStatus   [bool] Whether the user status information of all
                             one-to-one conversations should be loaded
                             (default false)
        #### Exceptions:
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
        """Create a new conversation.
        Method: POST
        Endpoint: /room

        #### Arguments:
        room_type	[str]	See constants list
        invite	[str]	user id (roomType = 1), group id (roomType = 2 - optional),
                        circle id (roomType = 2, source = 'circles'], only available
                        with circles-support capability))
        source	[str]	The source for the invite, only supported on roomType = 2 for
                        groups and circles (only available with circles-support capability)
        room_name	[str]	conversation name (Not available for roomType = 1)

        #### Exceptions:
        400 Bad Request When an invalid conversation type was given

        400 Bad Request When the conversation name is empty for type = 3

        401 Unauthorized When the user is not logged in

        404 Not Found When the target to invite does not exist
        """
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

        #### Exceptions:
        404 Not Found When the conversation could not be found for the participant
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


class Participant(object):
    """A conversation participant."""

    def __init__(self, data: dict, room: Conversation):
        self.__dict__.update(data)
        self.room = room
        self.api = self.room.api

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'Participant({self.actorId}, {self.room}, {self.displayName})'  # type: ignore

    def remove(self):
        """Delete an attendee from conversation.

        Method: DELETE
        Endpoint: /room/{token}/attendees

        #### Arguments:
        attendeeId	[int]	The participant to delete

        #### Exceptions:
        400 Bad Request When the participant is a moderator or owner

        400 Bad Request When there are no other moderators or owners left

        403 Forbidden When the current user is not a moderator or owner

        403 Forbidden When the participant to remove is an owner

        404 Not Found When the conversation could not be found for the participant

        404 Not Found When the participant to remove could not be found
        """
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.room.token}/attendees',  # type: ignore
            data={'attendeeId': self.attendeeId}  # type: ignore
        )

"""API interface."""

import xmltodict
import json

from typing import Union, List, Dict, Any
from nextcloud import NextCloud
from urllib.parse import urlencode
from urllib3 import HTTPResponse

from .rich_objects import NextCloudTalkRichObject

from .constants import (
    Permissions,
    ConversationType,
    NotificationLevel,
    ListableScope
)

from .exceptions import (
    NextCloudTalkException,
    NextCloudTalkBadRequest,
    NextCloudTalkForbidden,
    NextCloudTalkNotFound,
    NextCloudTalkConflict,
    NextCloudTalkPreconditionFailed,
    NextCloudTalkUnauthorized,
    NextCloudTalkNotCapable)


class NextCloudTalkAPI(object):
    """Base class for all API objects."""

    def __init__(self, client: NextCloud, api_endpoint: str):
        self.client = client
        self.endpoint = self.client.url + api_endpoint

    def query(
            self,
            data: dict = {},
            sub: str = '',
            method: str = 'GET',
            url: str = '',
            include_headers: list = []):
        """Submit query to almighty endpoint."""
        if method == 'GET':
            url_data = urlencode(data)
            request = self.client.session.request(
                url=f'{url}{sub}?{url_data}' if url else f'{self.endpoint}{sub}?{url_data}',
                method=method,
                headers={'OCS-APIRequest': 'true'})
        else:
            request = self.client.session.request(
                url=f'{url}{sub}' if url else f'{self.endpoint}{sub}',
                method=method,
                data=data,
                headers={'OCS-APIRequest': 'true'})

        if request.ok:
            # Convert OrderedDict from xmltodict.parse to regular dict.
            request_data = json.loads(json.dumps(xmltodict.parse(request.content)))
            try:
                ret = request_data['ocs']['data'] or {}
            except KeyError:
                raise NextCloudTalkException('Unable to parse response: ' + request_data)
            for header in include_headers:
                ret.setdefault('response_headers', {})\
                   .setdefault(header, request.headers.get(header, None))
        else:
            failure_data = xmltodict.parse(request.content)['ocs']['meta']
            exception_string = '[{statuscode}] {status}: {message}'.format(**failure_data)
            match failure_data['statuscode']:  # type: ignore
                case '400':
                    raise NextCloudTalkBadRequest(exception_string)
                case '401':
                    raise NextCloudTalkUnauthorized(exception_string)
                case '403':
                    raise NextCloudTalkForbidden(exception_string)
                case '404':
                    raise NextCloudTalkNotFound(exception_string)
                case '409':
                    raise NextCloudTalkConflict(exception_string)
                case '412':
                    raise NextCloudTalkPreconditionFailed(exception_string)
                case _:
                    raise NextCloudTalkException(exception_string)

        return ret


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
            status_update: bool = False,
            include_status: bool = False) -> List['Conversation']:
        """Return list of user's conversations.

        Method: GET
        Endpoint: /room

        #### Arguments:
        status_update  [bool]  Whether the "online" user status of the current
        user should be "kept-alive" (True) or not (False) (defaults to False)

        include_status   [bool] Whether the user status information of all
        one-to-one conversations should be loaded (default false)

        #### Exceptions:
        401 Unauthorized when the user is not logged in
        """
        data = {
            'noStatusUpdate': 1 if status_update else 0,
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
            source: str = '') -> 'Conversation':
        """Create a new conversation.
        Method: POST
        Endpoint: /room

        #### Arguments:
        room_type   [str]   See constants list
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

    def get(self, room_token: str) -> 'Conversation':
        """Get a specific conversation.

        Method: GET
        Endpoint: /room/{token}

        #### Exceptions:
        404 Not Found When the conversation could not be found for the participant
        """
        room_data = self.query(sub=f'/room/{room_token}')
        return Conversation(room_data, self)

    def open_conversation_list(self) -> List['Conversation']:
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


class ChatAPI(NextCloudTalkAPI):
    """Interface to the Conversations API.

    https://nextcloud-talk.readthedocs.io/en/latest/chat/
    """

    def __init__(self, client: NextCloud):
        """Initialize the Conversation API."""
        self.client = client
        if 'chat-v2' in self.client.capabilities:  # type: ignore
            self.api_endpoint = '/ocs/v2.php/apps/spreed/api/v1'
        else:
            raise NextCloudTalkNotCapable('Unable to determine chat endpoint.')

        super().__init__(client, api_endpoint=self.api_endpoint)


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
        roomName  [str]  New name for the conversation (1-200 characters)

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
        description [str] New description for the conversation

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

    def read_only(self, state: int) -> HTTPResponse:
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
        mode [str]	'default' or 'call', in case of call the permissions will be
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
        password	[str]	Optional: Password is only required for users
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

        sessionId   [str]  512 character long session string

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
        invitee	[str]	User, group, email or circle to add

        source  [str]	Source of the participant(s) as
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

    def send(self, *args, **kwargs):
        """Sending a new chat message

        Method: POST
        Endpoint: /chat/{token}
        Data:

        #### Arguments:
        message	[str]	The message the user wants to say

        actorDisplayName	[str]	Guest display name (ignored for logged in users)

        replyTo	[int]	The message ID this message is a reply to (only allowed for
                        messages from the same conversation and when the message type
                        is not system or command)

        referenceId	[str]	A reference string to be able to identify the message
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
        return self.chat.send(*args, **kwargs)

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

    def set_permissions_for_participants(
            self,
            permissions: Permissions,
            mode: str = 'add') -> HTTPResponse:
        """Set permissions for all attendees#
        Method: PUT
        Endpoint: /room/{token}/attendees/permissions/all

        #### Arguments:
        mode	[str]	Mode of how permissions should be manipulated.  See constants list.
        If the permissions were 0 (default) and the modification is add or remove, they will
        be initialised with the call or default conversation permissions before, falling back
        to 126 for moderators and 118 for normal participants.

        permissions	[int]	New permissions for the attendees, see constants list. If
        permissions are not 0 (default), the 1 (custom) permission will always be added.

        #### Exceptions:
        400 Bad Request When the conversation type does not support setting publishing
        permissions, e.g. one-to-one conversations

        400 Bad Request When the mode is invalid

        403 Forbidden When the current user is not a moderator, owner or guest moderator

        404 Not Found When the conversation could not be found for the participant
        """
        data = {
            'mode': mode,
            'permissions': permissions.value,
        }
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.room.token}/attendees/permissions/all',  # type: ignore
            data=data
        )

    def set_guest_display_name(
            self,
            display_name: str) -> HTTPResponse:
        """Set display name as a guest.

        API: Only v1
        Method: POST
        Endpoint: /guest/{token}/name

        #### Arguments:
        displayName	string	The new display name

        #### Exceptions:
        403 Forbidden When the current user is not a guest

        404 Not Found When the conversation could not be found for the
        participant
        """
        return self.api.query(
            method='POST',
            url=f'{self.api.client.url}/ocs/v2.php/apps/spreed/api/v1',
            sub=f'/guest/{self.token}/name',  # type: ignore
            data={'displayName': display_name}
        )

    def receive_messages(self, **kwargs) -> List['Message']:
        """Receive chat messages of a conversation.

        Method: GET
        Endpoint: /chat/{token}

        #### Arguments:
        look_into_future	[bool]	1 Poll and wait for new message or 0 get history
        of a conversation

        limit	[int]	Number of chat messages to receive (100 by default, 200 at most)

        last_known_message	[int]	Serves as an offset for the query. The lastKnownMessageId
        for the next page is available in the X-Chat-Last-Given header.

        last_common_read	[int]	Send the last X-Chat-Last-Common-Read header you got, if
        you are interested in updates of the common read value. A 304 response does not allow
        custom headers and otherwise the server can not know if your value is modified or not.

        timeout	[int]	$lookIntoFuture = 1 only, Number of seconds to wait for new messages
        (30 by default, 60 at most)

        set_read_marker	[bool]	True to automatically set the read timer after fetching the
        messages, use False when your client calls Mark chat as read manually. (Default: True)

        include_last_known    [bool]	True to include the last known message as well (Default:
        False)

        #### Exceptions:
        304 Not Modified When there were no older/newer messages

        404 Not Found When the conversation could not be found for the participant

        412 Precondition Failed When the lobby is active and the user is not a moderator

        #### Response Header:

        X-Chat-Last-Given	[int]	Offset (lastKnownMessageId) for the next page.
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that has
        read privacy set to public. When the user themself has it set to private the value
        the header is not set (only available with chat-read-status capability and when
        lastCommonReadId was sent)

        #### Response Data (As Message() object attributes):
        id	[int]	ID of the comment

        token	[str]	Conversation token

        actorType	[str]	See Constants - Actor types of chat messages

        actorId	[str]	Actor id of the message author

        actorDisplayName	[str]	Display name of the message author

        timestamp	[int]	Timestamp in seconds and UTC time zone

        systemMessage	[str]	empty for normal chat message or the type of the system message
        (untranslated)

        messageType	[str]	Currently known types are comment, comment_deleted, system
        and command

        isReplyable	[bool]	True if the user can post a reply to this message (only available
        with chat-replies capability)

        referenceId	[str]	A reference string that was given while posting the message to be
        able to identify a sent message again (available with chat-reference-id capability)

        message	[str]	Message string with placeholders (see Rich Object String)

        messageParameters	[array]	Message parameters for message (see Rich Object String)

        parent	[array]	Optional: See Parent data below

        reactions	[array]	Optional: An array map with relation between reaction emoji and
        total count of reactions with this emoji

        reactionsSelf	[array]	Optional: When the user reacted this is the list of emojis
        the user reacted with
        """
        return self.chat.receive_messages(**kwargs)

    def send_rich_object(self, *args, **kwargs):
        """Share a rich object to the chat.

        https://github.com/nextcloud/server/blob/master/lib/public/RichObjectStrings/Definitions.php

        Required capability: rich-object-sharing
        Method: POST
        Endpoint: /chat/{token}/share
        Data:

        #### Arguments:
        object_type	[str]	The object type

        object_id	[str]	The object id

        metadata	[str]	Array of the rich objects data

        actor_display_name	[str]   Guest display name (ignored for logged in users)

        reference_id	[str]	A reference string to be able to identify the message
        again in a "get messages" request, should be a random sha256 (only available
        with chat-reference-id capability)

        #### Exceptions:
        400 Bad Request In case the meta data is invalid

        403 Forbidden When the conversation is read-only

        404 Not Found When the conversation could not be found for the participant

        412 Precondition Failed When the lobby is active and the user is not a moderator

        413 Payload Too Large When the message was longer than the allowed limit of
        32000 characters (or 1000 until Nextcloud 16.0.1, check the spreed => config =>
        chat => max-length capability for the limit)

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that has
        read privacy set to public. When the user themself has it set to private the value
        the header is not set (only available with chat-read-status capability)

        #### Response Data:
        The full message array of the new message, as defined in Receive chat messages
        of a conversation
        """
        return self.chat.send_rich_object(*args, **kwargs)

    def clear_history(self) -> Dict[Any, Any]:
        """Clear chat history.

        Required capability: clear-history
        Method: DELETE
        Endpoint: /chat/{token}

        #### Exceptions:
        403 Forbidden When the user is not a moderator

        404 Not Found When the conversation could not be found for the participant

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that
        has read privacy set to public. When the user themself has it set to private
        the value the header is not set (only available with chat-read-status capability)

        #### Response Data:
        The full message array of the new system message "You cleared the history
        of the conversation", as defined in Receive chat messages of a conversation.  When
        rendering this message the client should also remove all messages from any
        cache/storage of the device.
        """
        return self.chat.clear_history()

    @property
    def chat_last_given(self):
        return self.chat.headers['X-Chat-Last-Given']

    @property
    def chat_last_common_read(self):
        return self.chat.headers['X-Chat-Last-Common-Read']

    def get_autocomplete_suggestions(
            self,
            search: str,
            limit: int = 20,
            include_status: bool = False) -> HTTPResponse:
        """Get mention autocomplete suggestions

        Method: GET
        Endpoint: /chat/{token}/mentions

        #### Arguments:
        search	[str]	Search term for name suggestions (should at least be 1 character)

        limit	[int]	Number of suggestions to receive (20 by default)

        include_status	[bool]	Whether the user status information also needs to be loaded

        #### Exceptions:
        403 Forbidden When the conversation is read-only

        404 Not Found When the conversation could not be found for the participant

        412 Precondition Failed When the lobby is active and the user is not a moderator

        #### Response Data:
        Each suggestion has at least:

        id	[str]	The user id which should be sent as @<id> in the message (user ids
        that contain spaces as well as guest ids need to be wrapped in double-quotes when
        sending in a message: @"space user" and @"guest/random-string")

        label	[str]	The displayname of the user

        source	[str]	The type of the user, currently only `users`, `guests` or `calls` (for
        mentioning the whole conversation)

        status	[str]	Optional: Only available with include_status=true and for users with a
        set status

        statusIcon	[str]	Optional: Only available with include_status=true and for users
        with a set status

        statusMessage	[str]	Optional: Only available with includeStatus=true and for
        users with a set status
        """
        return self.chat.api.query(
            method='GET',
            sub=f'/chat/{self.token}/mentions',  # type: ignore
            data={
                'search': search,
                'limit': limit,
                'includeStatus': include_status,
            }
        )

    def share_file(self, *args, **kwargs):
        """Share a file to the chat.

        Method: POST
        Endpoint: ocs/v2.php/apps/files_sharing/api/v1/shares

        #### Arguments:
        path	string	The file path inside the user's root to share

        reference_id	string	A reference string to be able to identify the generated chat
        message again in a "get messages" request, should be a random sha256 (only available
        with chat-reference-id capability)

        talkMetaData	[str]	JSON encoded array of the meta data

        #### talkMetaData:
        messageType [str]   A message type to show the message in different styles. Currently
        known: `voice-message` and `comment`
        """
        return self.chat.share_file(*args, **kwargs)


class Chat(object):
    """Represents a NextCloud Chat Object."""

    def __init__(self, token: str, chat_api: 'ChatAPI'):
        self.token = token
        self.api = chat_api
        self.headers = {}

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'Chat({self.token})'

    def receive_messages(
            self,
            look_into_future: bool = False,
            limit: int = 100,
            timeout: int = 30,
            last_known_message: int = 0,
            last_common_read: int = 0,
            set_read_marker: bool = True,
            include_last_known: bool = False) -> List['Message']:
        response = self.api.query(
            method='GET',
            sub=f'/chat/{self.token}',
            data={
                'lookIntoFuture': 1 if look_into_future else 0,
                'limit': limit,
                'lastKnownMessageId': last_known_message,
                'lastCommonReadId': last_common_read,
                'timeout': timeout,
                'setReadMaker': 1 if set_read_marker else 0,
                'includeLastKnown': 1 if include_last_known else 0
            },
            include_headers=['X-Chat-Last-Given', 'X-Chat-Last-Common-Read']
        )
        self.headers.update(response.get('response_headers', {}))
        if isinstance(response['element'], dict):
            return [Message(response['element'], self)]
        elif isinstance(response['element'], list):
            return [Message(x, self) for x in response['element']]
        else:
            raise NextCloudTalkException(f'Unknown return type for response: {response}')

    def send(
            self,
            message: str,
            reply_to: int = 0,
            display_name: Union[str, None] = None,
            reference_id: Union[str, None] = None,
            silent: bool = False) -> 'Message':
        """Send a text message to a conversation"""
        response = self.api.query(
            method='POST',
            sub=f'/chat/{self.token}',
            data={
                "message": message,
                "replyTo": reply_to,
                "displayName": display_name,
                "referenceId": reference_id,
                "silent": silent
            },
            include_headers=['X-Chat-Last-Common-Read']
        )
        self.headers.update(response.get('response_headers', {}))
        return Message(response, self)

    def share_file(
            self,
            path: str,
            reference_id: Union[str, None] = None,
            metadata_type: str = 'comment'):
        """Share a file to the chat.

        Method: POST
        Endpoint: ocs/v2.php/apps/files_sharing/api/v1/shares

        #### Arguments:
        path	string	The file path inside the user's root to share

        reference_id	string	A reference string to be able to identify the generated chat
        message again in a "get messages" request, should be a random sha256 (only available
        with chat-reference-id capability)

        talkMetaData	[str]	JSON encoded array of the meta data

        #### talkMetaData:
        messageType [str]   A message type to show the message in different styles. Currently
        known: `voice-message` and `comment`

        #### Exceptions:
        403 When path is already shared
        """
        self.api.query(
            method='POST',
            url=f'{self.api.client.url}/ocs/v2.php/apps/files_sharing/api/v1/shares',
            data={
                'shareType': 10,
                'shareWith': {self.token},
                'path': path,
                'reference_id': reference_id,
                'talkMetaData': json.dumps(
                    {'messageType': metadata_type}
                )
            }
        )

    def send_rich_object(
            self,
            rich_object: NextCloudTalkRichObject,
            reference_id: Union[str, None] = None,
            actor_display_name: str = 'Guest') -> Dict[Any, Any]:
        """Share a rich object to the chat.

        https://github.com/nextcloud/server/blob/master/lib/public/RichObjectStrings/Definitions.php

        Required capability: rich-object-sharing
        Method: POST
        Endpoint: /chat/{token}/share
        Data:

        #### Arguments:
        rich_object	[NextCloudTalkRichObject]	The rich object

        actor_display_name	[str]   Guest display name (ignored for logged in users)

        reference_id	[str]	A reference string to be able to identify the message
        again in a "get messages" request, should be a random sha256 (only available
        with chat-reference-id capability)

        #### Exceptions:
        400 Bad Request In case the meta data is invalid

        403 Forbidden When the conversation is read-only

        404 Not Found When the conversation could not be found for the participant

        412 Precondition Failed When the lobby is active and the user is not a moderator

        413 Payload Too Large When the message was longer than the allowed limit of
        32000 characters (or 1000 until Nextcloud 16.0.1, check the spreed => config =>
        chat => max-length capability for the limit)

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that has
        read privacy set to public. When the user themself has it set to private the value
        the header is not set (only available with chat-read-status capability)

        #### Response Data:
        The full message array of the new message, as defined in Receive chat messages
        of a conversation
        """
        response = self.api.query(
            method='POST',
            sub=f'/chat/{self.token}/share',
            data={
                'objectType': rich_object.object_type,
                'objectId': rich_object.id,
                'metaData': json.dumps(rich_object.metadata),
                'actorDisplayName': actor_display_name,
                'referenceId': reference_id
            },
            include_headers=['X-Chat-Last-Common-Read']
        )
        self.headers.update(response.get('response_headers', {}))
        return response

    def clear_history(self) -> Dict[Any, Any]:
        """Clear chat history.

        Required capability: clear-history
        Method: DELETE
        Endpoint: /chat/{token}

        #### Exceptions:
        403 Forbidden When the user is not a moderator

        404 Not Found When the conversation could not be found for the participant

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that
        has read privacy set to public. When the user themself has it set to private
        the value the header is not set (only available with chat-read-status capability)

        #### Response Data:
        The full message array of the new system message "You cleared the history
        of the conversation", as defined in Receive chat messages of a conversation.  When
        rendering this message the client should also remove all messages from any
        cache/storage of the device.
        """
        if 'clear-history' not in self.api.client.capabilities:  # type: ignore
            raise NextCloudTalkNotCapable('Server does not support deletion of chat history.')
        response = self.api.query(
            method='DELETE',
            sub=f'/chat/{self.token}',  # type: ignore
            include_headers=['X-Chat-Last-Common-Read'],
        )
        self.headers.update(response.get('response_headers', {}))
        return response

    @property
    def chat_last_given(self):
        return self.headers['X-Chat-Last-Given']

    @property
    def chat_last_common_read(self):
        return self.headers['X-Chat-Last-Common-Read']


class Participant(object):
    """A conversation participant."""

    actorId = None
    displayName = None
    attendeeId = None

    def __init__(self, data: dict, room: Conversation):
        self.__dict__.update(data)
        self.room = room
        self.api = self.room.api

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'Participant({self.actorId}, {self.room}, {self.displayName})'

    def remove(self) -> HTTPResponse:
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
            data={'attendeeId': self.attendeeId}
        )

    def promote(self) -> HTTPResponse:
        """Promote a user or guest to moderator.

        Method: POST
        Endpoint: /room/{token}/moderators

        #### Arguments:
        attendeeId	int	Attendee id can be used for guests and users

        #### Exceptions:
        400 Bad Request When the participant to promote is not a normal
        user (type 3) or normal guest (type 4)

        403 Forbidden When the current user is not a moderator or owner

        403 Forbidden When the participant to remove is an owner

        404 Not Found When the conversation could not be found for the
        participant

        404 Not Found When the participant to remove could not be found
        """
        return self.api.query(
            method='POST',
            sub=f'/room/{self.room.token}/moderators',  # type: ignore
            data={'attendeeId': self.attendeeId}
        )

    def demote(self) -> HTTPResponse:
        """Demote a moderator to user or guest.

        Method: DELETE
        Endpoint: /room/{token}/moderators

        #### Arguments:
        attendeeId	[int]	Attendee id can be used for guests and users

        #### Exceptions:
        400 Bad Request When the participant to demote is not a moderator
        (type 2) or guest moderator (type 6)

        403 Forbidden When the current participant is not a moderator or owner

        403 Forbidden When the current participant tries to demote themselves

        404 Not Found When the conversation could not be found for the participant

        404 Not Found When the participant to demote could not be found
        """
        return self.api.query(
            method='DELETE',
            sub=f'/room/{self.room.token}/moderators',  # type: ignore
            data={'attendeeId': self.attendeeId}
        )

    def set_permissions(
            self,
            permissions: Permissions,
            mode: str = 'add') -> HTTPResponse:
        """Set permissions for an attendee.

        Method: PUT
        Endpoint: /room/{token}/attendees/permissions

        #### Arguments:
        attendeeId	[int]	Attendee id can be used for guests and users

        mode	[str]	Mode of how permissions should be manipulated constants list.
        If the permissions were 0 (default) and the modification is `add` or `remove`,
        they will be initialised with the call or default conversation permissions
        before, falling back to 126 for moderators and 118 for normal participants.

        permissions	[Permissions()] New permissions for the attendee, see constants list.
        If permissions are not 0 (default), the 1 (custom) permission will always be
        added.

        #### Exceptions:
        400 Bad Request When the conversation type does not support setting publishing
        permissions, e.g. one-to-one conversations

        400 Bad Request When the attendee type is groups or circles

        400 Bad Request When the mode is invalid

        403 Forbidden When the current user is not a moderator, owner or guest moderator

        404 Not Found When the conversation could not be found for the participant

        404 Not Found When the attendee to set publishing permissions could not be found
        """
        data = {
            'attendeeId': self.attendeeId,
            'mode': mode,
            'permissions': permissions.value
        }
        return self.api.query(
            method='PUT',
            sub=f'/room/{self.room.token}/attendees/permissions',  # type: ignore
            data=data
        )


class Message(object):
    """A NextCloudTalk Message from a Conversation."""

    id = ''
    message = ''

    def __init__(self, data: dict, chat: Chat):
        self.__dict__.update(data)
        self.chat = chat

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'{self.__class__.__name__}'\
               f'({self.token}, {self.actorId}, {self.message})'  # type: ignore

    def delete(self) -> Dict[Any, Any]:
        """Delete a chat message.

        Required capability: delete-messages or rich-object-delete
        Method: DELETE
        Endpoint: /chat/{token}/{messageId}

        #### Exceptions:
        400 Bad Request The message is already older than 6 hours
        403 Forbidden When the message is not from the current user and the user not a
        moderator
        403 Forbidden When the conversation is read-only
        404 Not Found When the conversation or chat message could not be found for the
        participant
        405 Method Not Allowed When the message is not a normal chat message
        412 Precondition Failed When the lobby is active and the user is not a moderator

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that has read
        privacy set to public. When the user themself has it set to private the value the
        header is not set (only available with chat-read-status capability)

        #### Response Data:
        The full message array of the new system message "You deleted a message", as defined in
        Receive chat messages of a conversation The parent message is the object of the deleted
        message with the replaced text "Message deleted by you". This message should NOT be
        displayed to the user but instead be used to remove the original message from any
        cache/storage of the device.
        """
        if self.message == r'{object}':
            if 'rich-object-delete' not in self.chat.api.client.capabilities:  # type: ignore
                raise NextCloudTalkNotCapable(
                    'Server does not support deletion of rich objects.')
        else:
            if 'delete-messages' not in self.chat.api.client.capabilities:  # type: ignore
                raise NextCloudTalkNotCapable('Server does not support message deletion.')

        response = self.chat.api.query(
            method='DELETE',
            sub=f'/chat/{self.chat.token}/{self.id}',
            include_headers=['X-Chat-Last-Common-Read']
        )
        self.chat.headers.update(response['response_headers'])
        return response

    def mark_read(self) -> Dict[Any, Any]:
        """Mark chat as read.

        Required capability: chat-read-marker
        Method: POST
        Endpoint: /chat/{token}/read

        #### Arguments:
        lastReadMessage	[int]	The last read message ID

        #### Exceptions:
        404 Not Found When the room could not be found for the participant, or the
        participant is a guest.

        #### Response Header:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that
        has read privacy set to public. When the user themself has it set to private the
        value the header is not set (only available with chat-read-status capability)
        """
        response = self.chat.api.query(
            method='POST',
            sub=f'/chat/{self.chat.token}/read',
            data={'lastReadMessage': {self.id}},
            include_headers=['X-Chat-Last-Common-Read']
        )
        self.chat.headers.update(response.get('response_headers', {}))
        return response

    def mark_unread(self) -> Dict[Any, Any]:
        """Mark chat as unread.

        Required capability: chat-unread
        Method: DELETE
        Endpoint: /chat/{token}/read

        #### Exceptions:
        404 Not Found When the room could not be found for the participant, or the participant
        is a guest.

        #### Response Headers:
        X-Chat-Last-Common-Read	[int]	ID of the last message read by every user that has read
        privacy set to public. When the user themself has it set to private the value the
        header is not set (only available with chat-read-status capability)
        """
        response = self.chat.api.query(
            method='DELETE',
            sub=f'/chat/{self.chat.token}/read',
            include_headers=['X-Chat-Last-Common-Read']
        )
        self.chat.headers.update(response.get('response_headers', {}))
        return response

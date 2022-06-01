import json

from typing import Union

from nextcloud import NextCloud

from nctalk.api import NextCloudTalkAPI
from nctalk.exceptions import NextCloudTalkNotCapable
from nctalk.rich_objects import NextCloudTalkRichObject


class Chat(object):
    """Represents a NextCloud Chat Object."""

    def __init__(self, token: str, chat_api: 'ChatAPI'):
        self.token = token
        self.api = chat_api

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
            include_last_known: bool = False):
        return self.api.query(
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

    def send(
            self,
            message: str,
            reply_to: int = 0,
            display_name: Union[str, None] = None,
            reference_id: Union[str, None] = None,
            silent: bool = False):
        """Send a text message to a conversation"""
        return self.api.query(
            method='POST',
            sub=f'/chat/{self.token}',
            data={
                "message": message,
                "replyTo": reply_to,
                "displayName": display_name,
                "referenceId": reference_id,
                "silent": silent
            }
        )

    def send_rich_object(
            self,
            rich_object: NextCloudTalkRichObject,
            reference_id: Union[str, None] = None,
            actor_display_name: str = 'Guest'):
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
        return self.api.query(
            method='POST',
            sub=f'/chat/{self.token}/share',
            data={
                'objectType': rich_object.object_type,
                'objectId': rich_object.id,
                'metaData': json.dumps(rich_object.metadata()),
                'actorDisplayName': actor_display_name,
                'referenceId': reference_id
            }
        )

    def clear_history(self):
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
        return self.api.query(
            method='DELETE',
            sub=f'/chat/{self.token}'  # type: ignore
        )


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

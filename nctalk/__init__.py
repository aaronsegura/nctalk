"""NextCloud Talk client library."""
import xmltodict
import json

import importlib.metadata

from typing import List

from requests.auth import HTTPBasicAuth
from nextcloud import NextCloud

from .exceptions import NextCloudTalkException, NextCloudTalkUnauthorized

from . import api

__version__ = importlib.metadata.version('nctalk')


class NextCloudTalk(NextCloud):
    """Client for NextCloud Talk service.

    * Accepts same init parameters as NextCloud()
    * Exposes server capabilities and Talk-related config.php variables
    through the .capabilities and .config properties

    Example:

    >>> nct = NextCloudTalk(endpoint=endpoint, user=user, password=password)
    >>> nct.capabilities
    ['audio', 'video', 'chat-v2', 'conversation-v4', 'guest-signaling', 'empty-group-room',
    'guest-display-names', 'multi-room-users', 'favorites', 'last-room-activity', 'no-ping',
    'system-messages', 'delete-messages', 'mention-flag', 'in-call-flags',
    'conversation-call-flags', 'notification-levels', 'invite-groups-and-mails',
    'locked-one-to-one-rooms', 'read-only-rooms', 'listable-rooms', 'chat-read-marker',
    'webinary-lobby', 'start-call-flag', 'chat-replies', 'circles-support', 'force-mute',
    'sip-support', 'chat-read-status', 'phonebook-search', 'raise-hand', 'room-description',
    'rich-object-sharing', 'temp-user-avatar-api', 'geo-location-sharing',
    'voice-message-sharing', 'signaling-v3', 'publishing-permissions', 'clear-history',
    'direct-mention-flag', 'notification-calls', 'conversation-permissions',
    'chat-reference-id']
    >>> conversations = nct.conversation_list()
    >>> for c in conversations:
    ...   print(c.token, c.displayName, c.description)
    ...
    23pw7aud Work Chat None
    jit4tk78 Family Chat None
    6rsa4brg Talk updates ✅ None
    3vkymk5m Test public room None
    >>> message = conversations[0].send(message='hello')
    >>> print(message['id'])
    '4387'
    """

    __capabilities = []
    __config = {}
    __server_version = ''

    def __init__(
            self,
            endpoint: str,
            user: str = '',
            password: str = '',
            auth: HTTPBasicAuth = HTTPBasicAuth(None, None),
            **kwargs):
        """Initialize the NextCloud client."""

        if user and password:
            super().__init__(endpoint=endpoint, user=user, password=password, **kwargs)
        elif auth.username and auth.password:
            super().__init__(endpoint=endpoint, auth=auth, **kwargs)
        else:
            raise NextCloudTalkException("Incomplete credentials presented.")

        # get_user() in order to make this work.  If you don't get_user()
        # before making session requests you get {"message":"CSRF check failed"}
        # errors.
        self.user_data = self.get_user().json_data  # type: ignore

        if 'ocs' in self.user_data:
            data = self.user_data['ocs']['meta']
            raise NextCloudTalkUnauthorized(f'[{data["statuscode"]}] {data["message"]}')

        self.__conversation_api = None

    def conversation_list(
            self,
            status_update: bool = False,
            include_status: bool = False) -> List[api.Conversation]:
        """Return list of user's conversations."""
        return self.conversation_api.list(
            status_update=status_update,
            include_status=include_status)

    def conversation_create(
            self,
            room_type: str,
            invite: str,
            source: str = '',
            room_name: str = '') -> api.Conversation:
        """Create new conversation."""
        return self.conversation_api.new(
            room_type=room_type,
            invite=invite,
            source=source,
            room_name=room_name)

    def conversation_get(
            self,
            room_token: str) -> api.Conversation:
        """Get a specific conversation."""
        return self.conversation_api.get(
            room_token=room_token)

    def open_conversation_list(self) -> List[api.Conversation]:
        """Returns list of open public Conversations."""
        return self.conversation_api.open_conversation_list()

    def __populate_caches(self) -> None:
        """Populate the __capabilities and __config caches."""
        request = self.session.request(
            method='GET',
            url=self.url + '/ocs/v1.php/cloud/capabilities'
        )
        data = json.loads(json.dumps(xmltodict.parse(request.content)))
        try:
            self.__capabilities = \
                data['ocs']['data']['capabilities']['spreed']['features']['element']
            self.__config = data['ocs']['data']['capabilities']['spreed']['config']
            self.__server_version = data['ocs']['data']['version']['string']
        except TypeError:
            raise NextCloudTalkException("Unable to populate caches")

    @property
    def capabilities(self) -> List[str]:
        """Return list of advertised Talk capabilities."""
        if not self.__capabilities:
            self.__populate_caches()
        return self.__capabilities

    @property
    def config(self) -> dict:
        """Return Talk-related config.php variables."""
        if not self.__config:
            self.__populate_caches()
        return self.__config

    @property
    def server_version(self) -> str:
        """Return server version string."""
        if not self.__server_version:
            self.__populate_caches()
        return self.__server_version

    @property
    def conversation_api(self) -> api.ConversationAPI:
        """Return the Conversation API"""
        if not self.__conversation_api:
            self.__conversation_api = api.ConversationAPI(self)
        return self.__conversation_api

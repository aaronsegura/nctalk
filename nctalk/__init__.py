"""NextCloud Talk client library."""
import xmltodict
import json

import importlib.metadata

from requests.auth import HTTPBasicAuth
from nextcloud import NextCloud

from nctalk.conversations import Conversation, ConversationAPI
from nctalk.exceptions import NextCloudTalkException

__version__ = importlib.metadata.version('nctalk')


class NextCloudTalk(NextCloud):
    """Client for NextCloud Talk service."""

    __capabilities = []
    __config = {}

    def __init__(
            self,
            endpoint: str,
            user: str = '',
            password: str = '',
            auth: HTTPBasicAuth = HTTPBasicAuth(None, None)):
        """Initialize the NextCloud client."""

        if user and password:
            super().__init__(endpoint=endpoint, user=user, password=password)
        elif auth.username and auth.password:
            super().__init__(endpoint=endpoint, auth=auth)
        else:
            raise NextCloudTalkException("Incomplete credentials presented.")

        # get_user() in order to make this work.  If you don't get_user()
        # before making session requests you get {"message":"CSRF check failed"}
        # errors.
        self.user_data = self.get_user().json_data  # type: ignore

        self.conversation_api = ConversationAPI(self)

    def conversation_list(
            self,
            no_status_update: int = 0,
            include_status: bool = False) -> list:
        """Return list of user's conversations."""
        return self.conversation_api.list(
            no_status_update=no_status_update,
            include_status=include_status)

    def conversation_create(
            self,
            room_type: str,
            invite: str,
            source: str = '',
            room_name: str = '') -> Conversation:
        """Create new conversation."""
        return self.conversation_api.new(
            room_type=room_type,
            invite=invite,
            source=source,
            room_name=room_name)

    def conversation_get(
            self,
            room_token: str) -> Conversation:
        """Get a specific conversation."""
        return self.conversation_api.get(
            room_token=room_token)

    def open_conversation_list(self):
        """Returns list of open public Conversations."""
        return self.conversation_api.open_conversation_list()

    def __populate_caches(self):
        """Populate the __capabilities and __config caches."""
        request = self.session.request(
            method='GET',
            url=self.url + '/ocs/v1.php/cloud/capabilities'
        )
        data = json.loads(json.dumps(xmltodict.parse(request.content)))
        self.__capabilities = \
            data['ocs']['data']['capabilities']['spreed']['features']['element']
        self.__config = data['ocs']['data']['capabilities']['spreed']['config']

    @property
    def capabilities(self) -> list:
        """Return list of advertised Talk capabilities.

        Caches results to prevent multiple lookups.
        """
        if not self.__capabilities:
            self.__populate_caches()
        return self.__capabilities

    @property
    def config(self) -> dict:
        """Return Talk-related config.php variables.

        Caches results to prevent multiple lookups.
        """
        if not self.__config:
            self.__populate_caches()
        return self.__config

"""NextCloud Talk client library."""
import importlib.metadata
import xmltodict

from nextcloud import NextCloud

from nctalk.conversations import ConversationAPI, Conversation

__version__ = importlib.metadata.version('nctalk')


class NextCloudTalkException(Exception):
    """Generic Exception."""

    pass


class NextCloudTalk(object):
    """Client for NextCloud Talk service."""

    def __init__(self, endpoint: str = '', user: str = '', password: str = ''):
        """Initialize the NextCloud client."""
        self.endpoint = endpoint
        self.client = NextCloud(endpoint=endpoint, user=user, password=password)

        """get_user() in order to make I'm not sure exactly why this
        works, but if you don't get_user() before making session requests
        you get {"message":"CSRF check failed"} errors."""
        self.user_data = self.client.get_user()

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
            room_type: int,
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

    def conversation_rename(
            self,
            room_token: str,
            room_name: str):
        """Rename the conversation matching room_token."""
        room = self.conversation_get(room_token=room_token)
        return room.rename(room_name)

    def conversation_delete(
            self,
            room_token: str):
        """Delete the conversation matchin room_token."""
        room = self.conversation_get(room_token=room_token)
        return room.delete()

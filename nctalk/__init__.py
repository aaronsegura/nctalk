"""NextCloud Talk client library."""
import importlib.metadata

from nextcloud import NextCloud

from nctalk.conversations import ConversationAPI, Conversation

__version__ = importlib.metadata.version('nctalk')


class NextCloudTalk(NextCloud):
    """Client for NextCloud Talk service."""

    def __init__(self, endpoint: str = '', user: str = '', password: str = ''):
        """Initialize the NextCloud client."""
        super().__init__(endpoint=endpoint, user=user, password=password)

        # get_user() in order to make this work.  If you don't get_user()
        # before making session requests you get {"message":"CSRF check failed"}
        # errors.
        self.user_data = self.get_user()

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

    def open_conversation_list(self):
        """Returns list of open public Conversations."""
        return self.conversation_api.open_conversation_list()

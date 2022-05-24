from nextcloud import NextCloud

from nctalk.api import NextCloudTalkAPI

class Chat(object):
    """Represents a NextCloud Chat Object."""

    def __init__(self, token: str, chat_api: 'ChatAPI'):
        self.token = token
        self.api = chat_api

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

    def __str__(self):
        return f'Chat({self.token})'

    def send(
        self, 
        message: str, 
        reply_to: int = None, 
        display_name: str = None, 
        reference_id: str = None, 
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


class ChatAPI(NextCloudTalkAPI):
    """Interface to the Conversations API.

    https://nextcloud-talk.readthedocs.io/en/latest/chat/
    """

    def __init__(self, nextcloud_client: NextCloud):
        """Initialize the Conversation API."""
        self.api_endpoint = '/ocs/v2.php/apps/spreed/api/v1'
        super().__init__(nextcloud_client, api_endpoint=self.api_endpoint)

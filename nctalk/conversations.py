"""Conversation API."""

import xmltodict

from urllib.parse import urlencode
from nextcloud import NextCloud


CONVERSATION_TYPES = {
    "one_to_one": 1,
    "group": 2,
    "public": 3,
    "changelog": 4,
}


class ConversationException(Exception):
    """Our own little exception class."""

    pass


class Conversation(object):
    """Represents a NextCloud Talk Conversation."""

    def __init__(self, data: dict, conversation_api: 'ConversationAPI'):
        """Initialize object with data from  API."""
        self.__dict__.update(data)
        self.api = conversation_api

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.__dict__)

    def __str__(self):
        return 'Conversation({token}, {displayName}, {type})'.format(**self.__dict__)

    def rename(self, room_name: str):
        """Rename the room."""
        return self.api.query(
            method='PUT',
            sub='/room/{}'.format(self.token),
            data={'roomName': room_name})

    def delete(self):
        """Delete the room."""
        return self.api.query(
            method='DELETE',
            sub='/room/{}'.format(self.token))

    def description(self, description: str):
        """Set description on room."""
        req = self.api.query(
            method='PUT',
            sub='/room/{}/description'.format(self.token),
            data={'description': description})
        if req.ok:
            self.description = description
            return True
        else:
            raise ConversationException(req.content)


class ConversationAPI(object):
    """Interface to the Conversations API."""

    def __init__(self, nextcloud_client: NextCloud):
        """Initialize the Conversation API."""
        __ENDPOINT = '/ocs/v2.php/apps/spreed/api/v4'

        self.endpoint = nextcloud_client.endpoint + __ENDPOINT
        self.client = nextcloud_client.client

    def query(self, data: dict = {}, sub: str = '/room', method: str = 'GET'):
        """Submit query to almighty endpoint."""
        if method == 'GET':
            return self.client.session.request(
                url="{}{}{}{}".format(self.endpoint, sub, '?', urlencode(data)),
                method=method)
        else:
            return self.client.session.request(
                url="{}{}".format(self.endpoint, sub),
                method=method,
                data=data)

    def list(
            self,
            no_status_update: int = 0,
            include_status: bool = False) -> list:
        """Return list of user's conversations."""
        data = {
            'noStatusUpdate': no_status_update,
            'includeStatus': include_status,
        }
        request = self.query(data=data)
        if request.ok:
            rooms_data = xmltodict.parse(request.content)
            rooms = [
                Conversation(x, self)
                for x in rooms_data['ocs']['data']['element']
            ]
        else:
            raise ConversationException(request.content)

        return rooms

    def new(
            self,
            room_type: int,
            invite: str,
            room_name: str = '',
            source: str = '') -> Conversation:
        """Create a new conversation."""
        if type(room_type) is str:
            room_type = CONVERSATION_TYPES[room_type]

        data = {
            'roomType': room_type,
            'invite': invite,
            'source': source,
            'roomName': room_name
        }

        request = self.query(method="POST", data=data)
        if request.ok:
            data = xmltodict.parse(request.content)
            new_room = Conversation(data['ocs']['data'], self)
        else:
            raise ConversationException(request.content)

        return new_room

    def get(self, room_token: str) -> Conversation:
        """Get a specific conversation."""
        request = self.query(sub='/room/{}'.format(room_token))
        if request.ok:
            data = xmltodict.parse(request.content)
            room = Conversation(data['ocs']['data'], self)
        else:
            raise ConversationException(request.content)

        return room

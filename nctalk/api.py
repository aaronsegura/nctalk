"""Base API interface."""

import xmltodict

from nextcloud import NextCloud
from urllib.parse import urlencode


class NextCloudTalkException(Exception):
    """Generic Exception."""

    pass


class NextCloudTalkBadRequest(NextCloudTalkException):
    """User made a bad request."""

    pass


class NextCloudTalkUnauthorized(NextCloudTalkException):
    """User made a bad request."""

    pass


class NextCloudTalkForbidden(NextCloudTalkException):
    """User made a bad request."""

    pass


class NextCloudTalkNotFound(NextCloudTalkException):
    """User made a bad request."""

    pass


class NextCloudTalkAPI(object):
    """Base class for all API objects.

    * ConversationAPI
    * ChatAPI
    * ParticipantsAPI
    * WebinarAPI
    * etc...
    """

    def __init__(self, nextcloud_client: NextCloud, api_endpoint: str):
        """Initialize the Conversation API."""
        self.api_endpoint = api_endpoint

        self.endpoint = nextcloud_client.endpoint + self.api_endpoint
        self.client = nextcloud_client.client

    def query(self, data: dict = {}, sub: str = '', method: str = 'GET'):
        """Submit query to almighty endpoint."""
        if method == 'GET':
            url_data = urlencode(data)
            request = self.client.session.request(
                url=f'{self.endpoint}{sub}?{url_data}',
                method=method)
        else:
            request = self.client.session.request(
                url=f'{self.endpoint}{sub}',
                method=method,
                data=data)

        if request.ok:
            request_data = xmltodict.parse(request.content)
            try:
                ret = request_data['ocs']['data']
            except KeyError:
                raise NextCloudTalkException('Unable to parse response: ' + request_data)
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
                case _:
                    raise NextCloudTalkException(exception_string)

        return ret
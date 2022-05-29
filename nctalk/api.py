"""Base API interface."""

import xmltodict
import json

from nextcloud import NextCloud
from urllib.parse import urlencode


class NextCloudTalkException(Exception):
    """Generic Exception."""

    pass


class NextCloudTalkBadRequest(NextCloudTalkException):
    """400 - User made a bad request."""

    pass


class NextCloudTalkUnauthorized(NextCloudTalkException):
    """401 - User account is not authorized."""

    pass


class NextCloudTalkForbidden(NextCloudTalkException):
    """403 - Forbidden action due to permissions."""

    pass


class NextCloudTalkNotFound(NextCloudTalkException):
    """404 - Object was not found."""

    pass


class NextCloudTalkPreconditionFailed(NextCloudTalkException):
    """412 - User tried to join chat room without going to lobby."""

    pass


class NextCloudTalkAPI(object):
    """Base class for all API objects."""

    def __init__(self, client: NextCloud, api_endpoint: str):
        self.client = client
        self.endpoint = self.client.url + api_endpoint

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
            # Convert OrderedDict from xmltodict.parse to regular dict.
            request_data = json.loads(json.dumps(xmltodict.parse(request.content)))
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
                case '412':
                    raise NextCloudTalkPreconditionFailed(exception_string)
                case _:
                    raise NextCloudTalkException(exception_string)

        return ret

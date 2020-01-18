"""DNS over HTTPS client."""

import base64

from twisted.internet.defer import Deferred
from twisted.logger import Logger
from twisted.web.http_headers import Headers

from .agent import get_agent_for_address
from .util import BytesProducer
from .util import Gather


class HttpsClientError(Exception):
    """HTTPS client error."""

    def __init__(self, code, data):
        """Initialize."""

        self.code = code
        self.data = data
        super(HttpsClientError, self).__init__()

    def __str__(self):
        """Return string representation."""

        return 'HttpsClientError({code:}, {data!r})'.format(code=self.code, data=self.data)


class HttpsClient(object):
    """HTTPS client."""

    def __init__(self, reactor, uid, url, address):
        """Initialize."""
        self.reactor = reactor
        self.uid = uid
        self.url = url
        self.address = address
        self.agent = get_agent_for_address(reactor, address)

    def _request(self, url, body):
        self.log.debug('url: {url!s:}', url=url)

        finished = Deferred()

        d = self.agent.request(self.method,
                               bytes(url),
                               self.headers,
                               body)
        d.addCallback(self.handle_response, finished)
        d.addErrback(self.handle_error, finished)

        return finished

    def handle_response(self, response, finished):  # noqa: N802,D102
        if response.code == 200:
            self.log.debug('cache-control: {cc:}', cc=response.headers.getRawHeaders('cache-control'))
            d = Deferred()
            d.addCallback(self.return_response, finished)
            g = Gather(d)
            response.deliverBody(g)
        else:
            self.log.error('oops: {code:}', code=response.code)
            for key, values in response.headers.getAllRawHeaders():
                self.log.error('{key:}:', key=key)
                for value in values:
                    self.log.error('    {value:}', value=value)
            d = Deferred()
            d.addCallback(self.return_error, response.code, finished)
            g = Gather(d)
            response.deliverBody(g)

    def handle_error(self, failure, finished):  # noqa: N802,D102
        self.log.failure('oops', failure=failure)
        finished.errback(failure)

    def return_response(self, data, finished):  # noqa: N802,D102
        self.log.debug("received ({data!r})", data=data)
        finished.callback(data)

    def return_error(self, data, code, finished):
        self.log.debug('error data: {data:}', data=data)
        finished.errback(HttpsClientError(code, data))


class HttpsGetClient(HttpsClient):
    """Get answer using GET over https."""

    log = Logger()

    method = b'GET'
    headers = Headers({b'Accept': [b'application/dns-message']})

    def request(self, data):
        """Send request."""

        data = base64.urlsafe_b64encode(data).decode('us-ascii')

        url = self.url
        url = url.add('dns', data)
        url = url.add('ct', 'application/dns-message')

        return self._request(url, None)


class HttpsPostClient(HttpsClient):
    """Get answer using POST over https."""

    log = Logger()

    method = b'POST'
    headers = Headers({b'Content-Type': [b'application/dns-message'],
                       b'Accept': [b'application/dns-message']})

    def request(self, data):
        """Send request."""

        body = BytesProducer(data)

        return self._request(self.url, body)

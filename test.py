"""DOH Proxy."""

# noqa: D401

import base64
import sys

import dns.message
from hyperlink import URL
from zope.interface import implementer

from twisted.internet import reactor
from twisted.internet.address import IPv4Address
from twisted.internet.address import IPv6Address
from twisted.internet.defer import Deferred
from twisted.internet.defer import succeed
from twisted.internet.interfaces import IHostnameResolver
from twisted.internet.interfaces import IHostResolution
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.protocol import Protocol
from twisted.logger import FilteringLogObserver
from twisted.logger import Logger
from twisted.logger import LogLevel
from twisted.logger import LogLevelFilterPredicate
from twisted.logger import globalLogBeginner
from twisted.logger import textFileLogObserver
from twisted.web.client import Agent
from twisted.web.client import HTTPConnectionPool
from twisted.web.client import ResponseDone
from twisted.web.client import _HTTP11ClientFactory
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer


@implementer(IBodyProducer)
class BytesProducer(object):
    """Bytes producer."""

    log = Logger()

    def __init__(self, body):
        """Initalize."""
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):  # noqa N802
        """State producing."""
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):  # noqa N802
        """Pause producing."""
        pass

    def stopProducing(self):  # noqa N802
        """Stop producing."""
        pass


class GatherAndLog(Protocol):
    """Gather data and log results."""

    log = Logger()

    def __init__(self, finished=None):
        """Initialize."""
        self.buffer = []
        self.finished = finished

    def dataReceived(self, data):  # noqa: N802
        """Receeive a chunk of data."""
        self.buffer.append(data)

    def connectionLost(self, reason):  # noqa: N802
        """Remote connection lost."""
        if not isinstance(reason.value, ResponseDone):
            self.log.error('connection lost: {reason:}', reason=reason)

        buffer = b''.join(self.buffer)

        self.log.debug('{buffer:}', buffer=buffer)

        if self.finished is not None:
            self.finished.callback(buffer)


class Gather(Protocol):
    """Gather data from a remote request."""

    log = Logger()

    def __init__(self, finished=None):
        """Initialize."""
        self.buffer = []
        self.finished = finished

    def dataReceived(self, data):  # noqa: N802
        """Add more data."""
        self.buffer.append(data)

    def connectionMade(self):  # noqa: N802
        """Made connection."""
        self.log.debug("connection made")

    def connectionLost(self, reason):  # noqa: N802
        """Remote connection lost."""
        if not isinstance(reason.value, ResponseDone):
            self.log.debug('connection lost: {reason:}', reason=reason)

        buffer = b''.join(self.buffer)

        if self.finished is not None:
            self.finished.callback(buffer)


class QuietHTTP11ClientFactory(_HTTP11ClientFactory):
    """Less noisy version of _HTTP11ClientFactory."""

    noisy = False


@implementer(IHostResolution)
class MyHostResolution(object):
    """In progress resolution."""

    log = Logger()

    def __init__(self, name):
        """Initialize."""
        self.name = name
        self.log.debug('resolving {name:}', name=name)


@implementer(IHostnameResolver)
class MyResolver(object):
    """My resolver."""

    log = Logger()

    def __init__(self, reactor, address):
        """Initialize."""
        self.reactor = reactor
        self.address = address
        self.log.debug('initializeing resolver: {address:}', address=address)

    def resolveHostName(self, resolutionReceiver, hostName, portNumber=0,  # noqa: N802,N803
                        addressTypes=None, transportSemantics='TCP'):
        """Resolve a host name."""
        self.log.debug('resolution_receiver: {r!r:}', r=resolutionReceiver)
        self.log.debug('host_name: {h!r:}', h=hostName)
        self.log.debug('port_numer: {p!r}', p=portNumber)
        self.log.debug('address_types: {t!r}', t=addressTypes)
        self.log.debug('transport_semantics: {t!r}', t=transportSemantics)
        self.log.debug('resolving {hostname:} to {address:}', hostname=hostName, address=self.address)
        resolutionReceiver.resolutionBegan(MyHostResolution(hostName))
        resolutionReceiver.addressResolved(self.address)
        resolutionReceiver.resolutionComplete()
        return resolutionReceiver


class HttpsClient(object):
    """HTTPS client."""

    def __init__(self, agent, url):
        """Initialize."""
        self.agent = agent
        self.url = url

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
        self.log.error('oops: {code:}', code=response.code)
        for key, values in response.headers.getAllRawHeaders():
            self.log.error('{key:}:', key=key)
            for value in values:
                self.log.error('    {value:}', value=value)
        if response.code == 200:
            self.log.debug('cache-control: {cc:}', cc=response.headers.getRawHeaders('cache-control'))
            d = Deferred()
            d.addCallback(self.return_response, finished)
            g = Gather(d)
            response.deliverBody(g)
        else:
            # self.log.error('oops: {code:}', code=response.code)
            # for key, values in response.headers.getAllRawHeaders():
            #     self.log.error('{key:}:', key=key)
            #     for value in values:
            #         self.log.error('    {value:}', value=value)
            # finished.errback(None)
            g = GatherAndLog()
            response.deliverBody(g)

    def handle_error(self, failure, finished):  # noqa: N802,D102
        self.log.failure('oops', failure=failure)
        finished.errback(failure)

    def return_response(self, data, finished):  # noqa: N802,D102
        self.log.debug("received ({data!r})", data=data)
        finished.callback(data)


class HttpsGetClient(HttpsClient):
    """Get answer using GET over https."""

    log = Logger()

    method = b'GET'
    headers = Headers({b'Accept': [b'application/dns-message']})

    def request(self, data):
        """Send request."""

        data = base64.urlsafe_b64encode(data).decode('utf-8')

        url = self.url
        url = url.add('dns', data)
        url = url.add('ct', 'application/dns-message')

        return self._request(url, None)


class HttpsPostClient(HttpsClient):
    """Get answer using GET over https."""

    log = Logger()

    method = b'POST'
    headers = Headers({b'Content-Type': [b'application/dns-message'],
                       b'Accept': [b'application/dns-message']})

    def __init__(self, agent, url):
        """Initialize."""
        self.agent = agent
        self.url = url

    def request(self, data):
        """Send request."""

        body = BytesProducer(data)

        return self._request(self.url, body)


class UDPServer(DatagramProtocol):
    """UDP server."""

    log = Logger()

    def __init__(self, client):
        """Initialize."""

        self.client = client
        super(UDPServer, self).__init__()

    def startProtocol(self):  # noqa: N802,D102
        self.log.debug('started')

    def stopProtocol(self):  # noqa: N802,D102
        self.log.debug('stopped')

    def datagramReceived(self, data, address):  # noqa: N802,D102
        self.log.debug("received ({data!r}) from {address!s}", data=data, address=address)

        message = dns.message.from_wire(data)
        self.log.debug('request:\n{message!s}', message=message)

        d = self.client.request(data)
        d.addCallback(self.return_response, address)
        d.addErrback(self.error_response, address)

    def return_response(self, data, address):
        """Return response."""

        message = dns.message.from_wire(data)
        self.log.debug('response:\n{message!s}', message=message)

        self.transport.write(data, address)

    def error_response(self, failure, address):
        """Error response."""

        self.log.failure(failure)


def main():
    """Main server function."""

    log_filter = LogLevelFilterPredicate(LogLevel.debug)
    output = textFileLogObserver(sys.stderr)
    log_observer = FilteringLogObserver(observer=output,
                                        predicates=[log_filter])
    globalLogBeginner.beginLoggingTo([log_observer])

    pool = HTTPConnectionPool(reactor, persistent=True)
    pool.maxPersistentPerHost = 4
    pool._factory = QuietHTTP11ClientFactory
    agent = Agent(reactor, pool=pool)

    url = URL.from_text('https://doh.cleanbrowsing.org/doh/family-filter')
    client = HttpsPostClient(agent, url)

    resolver = MyResolver(reactor, IPv4Address('TCP', '185.228.168.168', url.port))
    reactor.installNameResolver(resolver)

    reactor.listenUDP(5300, UDPServer(client))

    reactor.run()


if __name__ == '__main__':
    main()

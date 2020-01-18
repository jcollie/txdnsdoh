
from zope.interface import implementer

from twisted.internet.endpoints import HostnameEndpoint
from twisted.internet.endpoints import wrapClientTLS
from twisted.logger import Logger
from twisted.web.client import Agent
from twisted.web.client import BrowserLikePolicyForHTTPS
from twisted.web.client import HTTPConnectionPool
from twisted.web.client import _HTTP11ClientFactory
from twisted.web.iweb import IAgentEndpointFactory


class QuietHTTP11ClientFactory(_HTTP11ClientFactory):
    """Less noisy version of _HTTP11ClientFactory."""

    noisy = False


@implementer(IAgentEndpointFactory)
class MyEndpointFactory(object):
    """Endpoint factory that will only connect to one specific address."""

    log = Logger()

    def __init__(self, reactor, address):
        """Initialize."""

        self.reactor = reactor
        self.address = address
        self.context_factory = BrowserLikePolicyForHTTPS()

    def endpointForURI(self, uri):  # noqa: N802
        """Create an endpoint for URI."""

        endpoint = HostnameEndpoint(self.reactor, self.address, uri.port)
        if uri.scheme == b'http':
            return endpoint
        elif uri.scheme == b'https':
            connection_creator = self.context_factory.creatorForNetloc(uri.host, uri.port)
            return wrapClientTLS(connection_creator, endpoint)


def get_agent_for_address(reactor, address):
    """Get an agent that will only connect to a specific IP address."""

    pool = HTTPConnectionPool(reactor, persistent=True)
    pool.maxPersistentPerHost = 2
    pool._factory = QuietHTTP11ClientFactory
    endpoint_factory = MyEndpointFactory(reactor, address)
    return Agent.usingEndpointFactory(reactor, endpoint_factory, pool=pool)

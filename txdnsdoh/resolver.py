"""Fake a resolver so that we completely bypass DNS or hosts file."""

from zope.interface import implementer

from twisted.internet.interfaces import IHostnameResolver
from twisted.internet.interfaces import IHostResolution
from twisted.logger import Logger


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
        self.log.debug('initializing resolver: {address:}', address=address)

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

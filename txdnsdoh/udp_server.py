"""UDP server."""


import dns.message
import dns.edns

from twisted.internet.protocol import DatagramProtocol
from twisted.logger import Logger


class UDPServer(DatagramProtocol):
    """UDP server."""

    log = Logger()
    noisy = False

    def __init__(self, client):
        """Initialize."""

        self.client = client
        super(UDPServer, self).__init__()

    def startProtocol(self):  # noqa: N802
        """Start operations."""

        self.log.debug('started')

    def stopProtocol(self):  # noqa: N802
        """Stop operations."""

        self.log.debug('stopped')

    def datagramReceived(self, data, address):  # noqa: N802
        """Receive a datagram from the wire."""

        self.log.debug("received ({data!r}) from {address!s}", data=data, address=address)

        message = dns.message.from_wire(data)
        self.log.debug('request:\n{message!s}', message=message)

        self.log.debug('edns request:\n{message:}', message=message)
        data = message.to_wire()

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

"""TCP server."""

import struct

import dns.message

from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.logger import Logger


class TCPServerFactory(Factory):
    """TCP server factory."""

    log = Logger()
    noisy = False

    def __init__(self, client):
        """Initialize."""
        self.client = client
        super(TCPServerFactory, self).__init__()

    def buildProtocol(self, address):  # noqa: N802
        """Build protocol."""
        self.log.debug('Building protocol for {address!r}', address=address)
        return TCPServer(address, self.client)


class TCPServer(Protocol):
    """TCP server."""

    log = Logger()
    noisy = False

    def __init__(self, address, client):
        """Initialize."""
        self.address = address
        self.client = client
        self.buffer = b''
        self.expecting = 0

        super(TCPServer, self).__init__()

    def connectionMade(self):  # noqa: N802
        """Connection made."""
        self.log.debug('connection made')

    def dataReceived(self, data):  # noqa: N802
        """Data received."""
        self.log.debug('received {length:} bytes', length=len(data))
        self.buffer += data
        while len(self.buffer) > self.expecting:
            if self.expecting == 0 and len(self.buffer) >= 2:
                self.expecting = struct.unpack('!H', self.buffer[:2])[0]
                self.buffer = self.buffer[2:]
                self.log.debug('expecting {expecting:} bytes', expecting=self.expecting)

            if self.expecting > 0 and len(self.buffer) >= self.expecting:
                data = self.buffer[:self.expecting]
                self.buffer = self.buffer[self.expecting:]
                self.expecting = 0
                self.log.debug('received {length:}\n{message!s:}', length=len(data), message=dns.message.from_wire(data))

                d = self.client.request(data)
                d.addCallback(self.return_response)
                d.addErrback(self.error_response)

        self.log.debug('{length:} bytes left in the buffer', length=len(self.buffer))

    def connectionLost(self, reason):  # noqa: N802
        """Connection lost."""
        if not reason.check(ConnectionDone):
            self.log.debug('connection lost: {reason!r}', reason=reason)
        else:
            self.log.debug('connection lost')

    def return_response(self, data):
        """Handle response from client."""

        self.log.debug('result:\n{message!s:}', message=dns.message.from_wire(data))
        length = struct.pack('!H', len(data))
        self.transport.write(length + data)

    def error_response(self, failure):
        """Handle error from client."""

        self.log.failure('oops', failure=failure)
        self.transport.loseConnection()

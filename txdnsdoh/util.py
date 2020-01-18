
"""Utilities."""

from zope.interface import implementer

from twisted.internet.defer import succeed
from twisted.internet.protocol import Protocol
from twisted.logger import Logger
from twisted.web.client import ResponseDone

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

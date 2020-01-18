"""DOH Proxy."""

# noqa: D401

import ipaddress
import sys

from hyperlink import URL
import yaml

from twisted.internet import reactor
from twisted.logger import FilteringLogObserver
from twisted.logger import Logger
from twisted.logger import LogLevel
from twisted.logger import LogLevelFilterPredicate
from twisted.logger import globalLogBeginner
from twisted.logger import textFileLogObserver

from .https_client import HttpsGetClient
from .https_client import HttpsPostClient
from .tcp_server import TCPServerFactory
from .udp_server import UDPServer


def main(reactor):
    """Main server function."""
    log = Logger()

    config = yaml.safe_load(open('config.yaml', 'rb'))

    upstreams = {}

    for upstream in config.get('upstreams', []):
        uid = upstream['id']

        url = URL.from_text(upstream['url'])

        try:
            address = str(ipaddress.ip_address(upstream['ip']))
        except ValueError:
            log.error('{address:} does not appear to be a valid IPv4 or IPv6 address!', address=address)
            continue

        method = upstream['method']

        if method == 'https_post':
            client = HttpsPostClient(reactor, uid, url, address)
            upstreams[uid] = client

        elif method == 'https_get':
            client = HttpsGetClient(reactor, uid, url, address)
            upstreams[uid] = client

        else:
            log.error('Unknown method {method:} on upstream {uid:}', method=method, uid=uid)

    # resolver = MyResolver(reactor, IPv4Address('TCP', '185.228.168.168', url.port))
    # reactor.installNameResolver(resolver)

    for server in config.get('server', {}).get('udp_listeners'):
        port = server['port']
        interface = server.get('interface', '')
        uid = server.get('upstream')
        client = upstreams[uid]
        reactor.listenUDP(port, UDPServer(client), interface=interface)

    for server in config.get('server', {}).get('tcp_listeners'):
        port = server['port']
        interface = server.get('interface', '')
        uid = server.get('upstream')
        client = upstreams[uid]
        reactor.listenTCP(port, TCPServerFactory(client), interface=interface)


if __name__ == '__main__':

    log_filter = LogLevelFilterPredicate(LogLevel.debug)
    output = textFileLogObserver(sys.stderr)
    log_observer = FilteringLogObserver(observer=output,
                                        predicates=[log_filter])
    globalLogBeginner.beginLoggingTo([log_observer])

    reactor.callWhenRunning(main, reactor)
    reactor.run()

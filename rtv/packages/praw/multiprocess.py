"""Provides a request server to be used with the multiprocess handler."""

from __future__ import print_function, unicode_literals

import socket
import sys
from optparse import OptionParser
from praw import __version__
from praw.handlers import DefaultHandler
from requests import Session
from six.moves import cPickle, socketserver  # pylint: disable=F0401
from threading import Lock


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # pylint: disable=R0903,W0232
    """A TCP server that creates new threads per connection."""

    allow_reuse_address = True

    @staticmethod
    def handle_error(_, client_addr):
        """Mute tracebacks of common errors."""
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type is socket.error and exc_value[0] == 32:
            pass
        elif exc_type is cPickle.UnpicklingError:
            sys.stderr.write('Invalid connection from {0}\n'
                             .format(client_addr[0]))
        else:
            raise


class RequestHandler(socketserver.StreamRequestHandler):
    # pylint: disable=W0232
    """A class that handles incoming requests.

    Requests to the same domain are cached and rate-limited.

    """

    ca_lock = Lock()  # lock around cache and timeouts
    cache = {}  # caches requests
    http = Session()  # used to make requests
    last_call = {}  # Stores a two-item list: [lock, previous_call_time]
    rl_lock = Lock()  # lock used for adding items to last_call
    timeouts = {}  # store the time items in cache were entered

    do_evict = DefaultHandler.evict  # Add in the evict method

    @staticmethod
    def cache_hit_callback(key):
        """Output when a cache hit occurs."""
        print('HIT {0} {1}'.format('POST' if key[1][1] else 'GET', key[0]))

    @DefaultHandler.with_cache
    @DefaultHandler.rate_limit
    def do_request(self, request, proxies, timeout, **_):
        """Dispatch the actual request and return the result."""
        print('{0} {1}'.format(request.method, request.url))
        response = self.http.send(request, proxies=proxies, timeout=timeout,
                                  allow_redirects=False)
        response.raw = None  # Make pickleable
        return response

    def handle(self):
        """Parse the RPC, make the call, and pickle up the return value."""
        data = cPickle.load(self.rfile)  # pylint: disable=E1101
        method = data.pop('method')
        try:
            retval = getattr(self, 'do_{0}'.format(method))(**data)
        except Exception as e:
            # All exceptions should be passed to the client
            retval = e
        cPickle.dump(retval, self.wfile,  # pylint: disable=E1101
                     cPickle.HIGHEST_PROTOCOL)


def run():
    """The entry point from the praw-multiprocess utility."""
    parser = OptionParser(version='%prog {0}'.format(__version__))
    parser.add_option('-a', '--addr', default='localhost',
                      help=('The address or host to listen on. Specify -a '
                            '0.0.0.0 to listen on all addresses. '
                            'Default: localhost'))
    parser.add_option('-p', '--port', type='int', default='10101',
                      help=('The port to listen for requests on. '
                            'Default: 10101'))
    options, _ = parser.parse_args()
    try:
        server = ThreadingTCPServer((options.addr, options.port),
                                    RequestHandler)
    except (socket.error, socket.gaierror) as exc:  # Handle bind errors
        print(exc)
        sys.exit(1)
    print('Listening on {0} port {1}'.format(options.addr, options.port))
    try:
        server.serve_forever()  # pylint: disable=E1101
    except KeyboardInterrupt:
        server.socket.close()  # pylint: disable=E1101
        RequestHandler.http.close()
        print('Goodbye!')

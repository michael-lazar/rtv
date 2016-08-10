# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import time
import uuid
import string
import codecs
import logging
import threading

#pylint: disable=import-error
from six.moves.urllib.parse import urlparse, parse_qs
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from . import docs
from .config import TEMPLATES


_logger = logging.getLogger(__name__)

INDEX = os.path.join(TEMPLATES, 'index.html')


class OAuthHandler(BaseHTTPRequestHandler):

    # params are stored as a global because we don't have control over what
    # gets passed into the handler __init__. These will be accessed by the
    # OAuthHelper class.
    params = {'state': None, 'code': None, 'error': None}
    shutdown_on_request = True

    def do_GET(self):
        """
        Accepts GET requests to http://localhost:6500/, and stores the query
        params in the global dict. If shutdown_on_request is true, stop the
        server after the first successful request.

        The http request may contain the following query params:
            - state : unique identifier, should match what we passed to reddit
            - code  : code that can be exchanged for a refresh token
            - error : if provided, the OAuth error that occurred
        """

        parsed_path = urlparse(self.path)
        if parsed_path.path != '/':
            self.send_error(404)

        qs = parse_qs(parsed_path.query)
        self.params['state'] = qs['state'][0] if 'state' in qs else None
        self.params['code'] = qs['code'][0] if 'code' in qs else None
        self.params['error'] = qs['error'][0] if 'error' in qs else None

        body = self.build_body()

        # send_response also sets the Server and Date headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=UTF-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()

        self.wfile.write(body)

        if self.shutdown_on_request:
            # Shutdown the server after serving the request
            # http://stackoverflow.com/a/22533929
            thread = threading.Thread(target=self.server.shutdown)
            thread.daemon = True
            thread.start()

    def log_message(self, format, *args):
        """
        Redirect logging to our own handler instead of stdout
        """
        _logger.debug(format, *args)

    def build_body(self, template_file=INDEX):
        """
        Params:
            template_file (text): Path to an index.html template

        Returns:
            body (bytes): THe utf-8 encoded document body
        """

        if self.params['error'] == 'access_denied':
            message = docs.OAUTH_ACCESS_DENIED
        elif self.params['error'] is not None:
            message = docs.OAUTH_ERROR.format(error=self.params['error'])
        elif self.params['state'] is None or self.params['code'] is None:
            message = docs.OAUTH_INVALID
        else:
            message = docs.OAUTH_SUCCESS

        with codecs.open(template_file, 'r', 'utf-8') as fp:
            index_text = fp.read()

        body = string.Template(index_text).substitute(message=message)
        body = codecs.encode(body, 'utf-8')
        return body


class OAuthHelper(object):

    params = OAuthHandler.params

    def __init__(self, reddit, term, config):

        self.term = term
        self.reddit = reddit
        self.config = config

        # Wait to initialize the server, we don't want to reserve the port
        # unless we know that the server needs to be used.
        self.server = None

        self.reddit.set_oauth_app_info(
            self.config['oauth_client_id'],
            self.config['oauth_client_secret'],
            self.config['oauth_redirect_uri'])

        # Reddit's mobile website works better on terminal browsers
        if not self.term.display:
            if '.compact' not in self.reddit.config.API_PATHS['authorize']:
                self.reddit.config.API_PATHS['authorize'] += '.compact'

    def authorize(self):

        self.params.update(state=None, code=None, error=None)

        # If we already have a token, request new access credentials
        if self.config.refresh_token:
            with self.term.loader('Logging in'):
                self.reddit.refresh_access_information(
                    self.config.refresh_token)
            return

        state = uuid.uuid4().hex
        authorize_url = self.reddit.get_authorize_url(
            state, scope=self.config['oauth_scope'], refreshable=True)

        if self.server is None:
            address = ('', self.config['oauth_redirect_port'])
            self.server = HTTPServer(address, OAuthHandler)

        if self.term.display:
            # Open a background browser (e.g. firefox) which is non-blocking.
            # The server will block until it responds to its first request,
            # at which point we can check the callback params.
            OAuthHandler.shutdown_on_request = True
            with self.term.loader('Opening browser for authorization'):
                self.term.open_browser(authorize_url)
                self.server.serve_forever()
            if self.term.loader.exception:
                # Don't need to call server.shutdown() because serve_forever()
                # is wrapped in a try-finally that doees it for us.
                return
        else:
            # Open the terminal webbrowser in a background thread and wait
            # while for the user to close the process. Once the process is
            # closed, the iloop is stopped and we can check if the user has
            # hit the callback URL.
            OAuthHandler.shutdown_on_request = False
            with self.term.loader('Redirecting to reddit', delay=0):
                # This load message exists to provide user feedback
                time.sleep(1)

            thread = threading.Thread(target=self.server.serve_forever)
            thread.daemon = True
            thread.start()
            try:
                self.term.open_browser(authorize_url)
            except Exception as e:
                # If an exception is raised it will be seen by the thread
                # so we don't need to explicitly shutdown() the server
                _logger.exception(e)
                self.term.show_notification('Browser Error')
            else:
                self.server.shutdown()
            finally:
                thread.join()

        if self.params['error'] == 'access_denied':
            self.term.show_notification('Denied access')
            return
        elif self.params['error']:
            self.term.show_notification('Authentication error')
            return
        elif self.params['state'] is None:
            # Something went wrong but it's not clear what happened
            return
        elif self.params['state'] != state:
            self.term.show_notification('UUID mismatch')
            return

        with self.term.loader('Logging in'):
            info = self.reddit.get_access_information(self.params['code'])
        if self.term.loader.exception:
            return

        message = 'Welcome {}!'.format(self.reddit.user.name)
        self.term.show_notification(message)

        self.config.refresh_token = info['refresh_token']
        if self.config['persistent']:
            self.config.save_refresh_token()

    def clear_oauth_data(self):
        self.reddit.clear_authentication()
        self.config.delete_refresh_token()
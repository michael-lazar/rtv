# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import uuid

from concurrent.futures import ThreadPoolExecutor
from tornado import gen, ioloop, web, httpserver

from .config import TEMPLATE


class OAuthHandler(web.RequestHandler):
    """
    Intercepts the redirect that Reddit sends the user to after they verify or
    deny the application access.

    The GET should supply 3 request params:
        state: Unique id that was supplied by us at the beginning of the
               process to verify that the session matches.
        code: Code that we can use to generate the refresh token.
        error: If an error occurred, it will be placed here.
    """

    def initialize(self, display=None, params=None):
        self.display = display
        self.params = params

    def get(self):
        self.params['state'] = self.get_argument('state', default=None)
        self.params['code'] = self.get_argument('code', default=None)
        self.params['error'] = self.get_argument('error', default=None)

        self.render('index.html', **self.params)

        complete = self.params['state'] and self.params['code']
        if complete or self.params['error']:
            # Stop IOLoop if using a background browser such as firefox
            if self.display:
                ioloop.IOLoop.current().stop()


class OAuthHelper(object):

    def __init__(self, reddit, term, config):

        self.term = term
        self.reddit = reddit
        self.config = config

        self.http_server = None
        self.params = {'state': None, 'code': None, 'error': None}

        # Initialize Tornado webapp
        # Pass a mutable params object so the request handler can modify it
        kwargs = {'display': self.term.display, 'params': self.params}
        routes = [('/', OAuthHandler, kwargs)]
        self.callback_app = web.Application(
            routes, template_path=TEMPLATE)

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

        # https://github.com/tornadoweb/tornado/issues/1420
        io = ioloop.IOLoop.current()

        # Start the authorization callback server
        if self.http_server is None:
            self.http_server = httpserver.HTTPServer(self.callback_app)
            self.http_server.listen(self.config['oauth_redirect_port'])

        state = uuid.uuid4().hex
        authorize_url = self.reddit.get_authorize_url(
            state, scope=self.config['oauth_scope'], refreshable=True)

        if self.term.display:
            # Open a background browser (e.g. firefox) which is non-blocking.
            # Stop the iloop when the user hits the auth callback, at which
            # point we continue and check the callback params.
            with self.term.loader('Opening browser for authorization'):
                self.term.open_browser(authorize_url)
                io.start()
            if self.term.loader.exception:
                return
        else:
            # Open the terminal webbrowser in a background thread and wait
            # while for the user to close the process. Once the process is
            # closed, the iloop is stopped and we can check if the user has
            # hit the callback URL.
            with self.term.loader('Redirecting to reddit', delay=0):
                # This load message exists to provide user feedback
                time.sleep(1)
            io.add_callback(self._async_open_browser, authorize_url)
            io.start()

        if self.params['error'] == 'access_denied':
            self.term.show_notification('Declined access')
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

    @gen.coroutine
    def _async_open_browser(self, url):
        with ThreadPoolExecutor(max_workers=1) as executor:
            yield executor.submit(self.term.open_browser, url)
        ioloop.IOLoop.current().stop()
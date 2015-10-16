import os
import time
import uuid

import praw
from tornado import gen, ioloop, web, httpserver
from concurrent.futures import ThreadPoolExecutor

from . import config
from .curses_helpers import show_notification
from .helpers import check_browser_display, open_browser

__all__ = ['OAuthTool']

oauth_state = None
oauth_code = None
oauth_error = None

template_path = os.path.join(os.path.dirname(__file__), 'templates')


class AuthHandler(web.RequestHandler):

    def get(self):
        global oauth_state, oauth_code, oauth_error

        oauth_state = self.get_argument('state', default='placeholder')
        oauth_code = self.get_argument('code', default='placeholder')
        oauth_error = self.get_argument('error', default='placeholder')

        self.render('index.html', state=oauth_state, code=oauth_code,
                    error=oauth_error)

        # Stop IOLoop if using a background browser such as firefox
        if check_browser_display():
            ioloop.IOLoop.current().stop()


class OAuthTool(object):

    def __init__(self, reddit, stdscr=None, loader=None):

        self.reddit = reddit
        self.stdscr = stdscr
        self.loader = loader
        self.http_server = None

        self.refresh_token = config.load_refresh_token()

        # Initialize Tornado webapp
        routes = [('/', AuthHandler)]
        self.callback_app = web.Application(routes,
                                            template_path=template_path)

        self.reddit.set_oauth_app_info(config.oauth_client_id,
                                       config.oauth_client_secret,
                                       config.oauth_redirect_uri)

        # Reddit's mobile website works better on terminal browsers
        if not check_browser_display():
            if '.compact' not in self.reddit.config.API_PATHS['authorize']:
                self.reddit.config.API_PATHS['authorize'] += '.compact'

    def authorize(self):

        # If we already have a token, request new access credentials
        if self.refresh_token:
            with self.loader(message='Logging in'):
                self.reddit.refresh_access_information(self.refresh_token)
                return

        # Start the authorization callback server
        if self.http_server is None:
            self.http_server = httpserver.HTTPServer(self.callback_app)
            self.http_server.listen(config.oauth_redirect_port)

        hex_uuid = uuid.uuid4().hex
        authorize_url = self.reddit.get_authorize_url(
            hex_uuid, scope=config.oauth_scope, refreshable=True)

        # Open the browser and wait for the user to authorize the app
        if check_browser_display():
            with self.loader(message='Waiting for authorization'):
                open_browser(authorize_url)
                ioloop.IOLoop.current().start()
        else:
            with self.loader(delay=0, message='Redirecting to reddit'):
                # Provide user feedback
                time.sleep(1)
            ioloop.IOLoop.current().add_callback(self._open_authorize_url,
                                                 authorize_url)
            ioloop.IOLoop.current().start()

        if oauth_error == 'access_denied':
            show_notification(self.stdscr, ['Declined access'])
            return
        elif oauth_error != 'placeholder':
            show_notification(self.stdscr, ['Authentication error'])
            return
        elif hex_uuid != oauth_state:
            # Check if UUID matches obtained state.
            # If not, authorization process is compromised.
            show_notification(self.stdscr, ['UUID mismatch'])
            return

        try:
            with self.loader(message='Logging in'):
                access_info = self.reddit.get_access_information(oauth_code)
                self.refresh_token = access_info['refresh_token']
                if config.persistent:
                    config.save_refresh_token(access_info['refresh_token'])
        except (praw.errors.OAuthAppRequired, praw.errors.OAuthInvalidToken):
            show_notification(self.stdscr, ['Invalid OAuth data'])
        else:
            message = ['Welcome {}!'.format(self.reddit.user.name)]
            show_notification(self.stdscr, message)

    def clear_oauth_data(self):
        self.reddit.clear_authentication()
        config.clear_refresh_token()
        self.refresh_token = None

    @gen.coroutine
    def _open_authorize_url(self, url):
        with ThreadPoolExecutor(max_workers=1) as executor:
            yield executor.submit(open_browser, url)
        ioloop.IOLoop.current().stop()

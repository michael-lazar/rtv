import curses
import logging
import os
import time
import uuid
import webbrowser

import praw
from six.moves import configparser

from . import config
from .curses_helpers import show_notification, prompt_input

from tornado import ioloop, web

__all__ = ['token_validity', 'OAuthToolCompact', 'OAuthTool']
_logger = logging.getLogger(__name__)

oauth_state = None
oauth_code = None
oauth_error = None

class HomeHandler(web.RequestHandler):

    def get(self):
        self.render('home.html')

class AuthHandler(web.RequestHandler):

    def get(self):
        try:
            global oauth_state
            global oauth_code
            global oauth_error

            oauth_state = self.get_argument('state', default='state_placeholder')
            oauth_code = self.get_argument('code', default='code_placeholder')
            oauth_error = self.get_argument('error', default='error_placeholder')

            self.render('auth.html', state=oauth_state, code=oauth_code, error=oauth_error)
        finally:
            ioloop.IOLoop.current().stop()

class OAuthToolCompact(object):

    def __init__(self, reddit, client_id=None, redirect_uri=None, scope=None):
        self.reddit = reddit

        self.config = configparser.ConfigParser()
        self.config_fp = None

        self.client_id = client_id or config.oauth_client_id
        # Comply with PRAW's desperate need for client secret
        self.client_secret = config.oauth_client_secret
        self.redirect_uri = redirect_uri or config.oauth_redirect_uri

        self.scope = scope or config.oauth_scope.split('-')

        self.access_info = {}

        # Initialize Tornado webapp and listen on port 65000
        self.callback_app = web.Application([
            (r'/', HomeHandler),
            (r'/auth', AuthHandler),
        ], template_path='rtv/templates')
        self.callback_app.listen(65000)

    def get_config_fp(self):
        HOME = os.path.expanduser('~')
        XDG_CONFIG_HOME = os.getenv('XDG_CONFIG_HOME',
            os.path.join(HOME, '.config'))

        if os.path.exists(os.path.join(XDG_CONFIG_HOME, 'rtv')):
            file_path = os.path.join(XDG_CONFIG_HOME, 'rtv', 'oauth.cfg')
        else:
            file_path = os.path.join(HOME, '.rtv-oauth')

        return file_path

    def open_config(self, update=False):
        if self.config_fp is None:
            self.config_fp = self.get_config_fp()

        if update:
            self.config.read(self.config_fp)

    def save_config(self):
        self.open_config()
        with open(self.config_fp, 'w') as cfg:
            self.config.write(cfg)

    def authorize(self):
        self.reddit.set_oauth_app_info(self.client_id,
            self.client_secret,
            self.redirect_uri)

        self.open_config(update=True)
        # Generate a random UUID
        hex_uuid = uuid.uuid4().hex

        permission_ask_page_link = self.reddit.get_authorize_url(str(hex_uuid),
            scope=self.scope, refreshable=True)

        print('Opening permission asking page in {}'.format(os.environ.get('BROWSER')))
        webbrowser.open(permission_ask_page_link)
        ioloop.IOLoop.current().start()

        global oauth_state
        global oauth_code
        global oauth_error

        self.final_state = oauth_state
        self.final_code = oauth_code
        self.final_error = oauth_error

        # Check if access was denied
        if self.final_error == 'access_denied':
            print('Declined access')
            return
        elif self.final_error != 'error_placeholder':
            print('Authentication error')
            return

        # Check if UUID matches obtained state
        # (if not, authorization process is compromised, and I'm giving up)
        if hex_uuid != self.final_state:
            print('UUID mismatch, stopping.')
            return

        try:
            print('Logging in...')
            # Get access information (tokens and scopes)
            self.access_info = self.reddit.get_access_information(self.final_code)
        except (praw.errors.OAuthAppRequired, praw.errors.OAuthInvalidToken) as e:
            print('Error : Invalid OAuth data')
        else:
            if not self.config.has_section('oauth'):
                self.config.add_section('oauth')

            self.config.set('oauth', 'refresh_token', self.access_info['refresh_token'])
            self.save_config()

class OAuthTool(OAuthToolCompact):

    def __init__(self, reddit, stdscr=None, loader=None,
                client_id=None, redirect_uri=None, scope=None):
        super(OAuthTool, self).__init__(reddit, client_id, redirect_uri, scope)
        self.stdscr = stdscr
        self.loader = loader

    def authorize(self):
        self.reddit.set_oauth_app_info(self.client_id,
            self.client_secret,
            self.redirect_uri)

        self.open_config(update=True)
        # Generate a random UUID
        hex_uuid = uuid.uuid4().hex

        permission_ask_page_link = self.reddit.get_authorize_url(str(hex_uuid),
            scope=self.scope, refreshable=True)

        with self.loader(message='Waiting for authorization'):
            webbrowser.open(permission_ask_page_link)
            ioloop.IOLoop.current().start()

        global oauth_state
        global oauth_code
        global oauth_error

        self.final_state = oauth_state
        self.final_code = oauth_code
        self.final_error = oauth_error

        # Check if access was denied
        if self.final_error == 'access_denied':
            show_notification(self.stdscr, ['Declined access'])
            return
        elif self.final_error != 'error_placeholder':
            show_notification(self.stdscr, ['Authentication error'])
            return

        # Check if UUID matches obtained state
        # (if not, authorization process is compromised, and I'm giving up)
        if hex_uuid != self.final_state:
            show_notification(self.stdscr, ['UUID mismatch, stopping.'])
            return

        try:
            with self.loader(message='Logging in'):
                # Get access information (tokens and scopes)
                self.access_info = self.reddit.get_access_information(self.final_code)
        except (praw.errors.OAuthAppRequired, praw.errors.OAuthInvalidToken) as e:
            show_notification(self.stdscr, ['Invalid OAuth data'])
        else:
            if not self.config.has_section('oauth'):
                self.config.add_section('oauth')

            self.config.set('oauth', 'refresh_token', self.access_info['refresh_token'])
            self.save_config()

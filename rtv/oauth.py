import configparser
import curses
import logging
import os
import time
import uuid
import webbrowser

import praw

from . import config
from .curses_helpers import show_notification, prompt_input

__all__ = ['token_validity', 'OAuthTool']
_logger = logging.getLogger(__name__)

token_validity = 3540

class OAuthTool(object):

    def __init__(self, reddit, stdscr=None, loader=None,
                client_id=None, redirect_uri=None, scope=None):
        self.reddit = reddit
        self.stdscr = stdscr
        self.loader = loader

        self.config = configparser.ConfigParser()
        self.config_fp = None

        self.client_id = client_id or config.oauth_client_id
        # Comply with PRAW's desperate need for client secret
        self.client_secret = config.oauth_client_secret
        self.redirect_uri = redirect_uri or config.oauth_redirect_uri

        self.scope = scope or config.oauth_scope.split('-')

        self.access_info = {}

        self.token_expiration = 0

    def get_config_fp(self):
        HOME = os.path.expanduser('~')
        XDG_CONFIG_HOME = os.getenv('XDG_CONFIG_HOME',
            os.path.join(HOME, '.config'))

        config_paths = [
            os.path.join(XDG_CONFIG_HOME, 'rtv', 'rtv.cfg'),
            os.path.join(HOME, '.rtv')
        ]

        # get the first existing config file
        for config_path in config_paths:
            if os.path.exists(config_path):
                break

        return config_path

    def open_config(self, update=False):
        if self.config_fp is None:
            self.config_fp = self.get_config_fp()

        if update:
            self.config.read(self.config_fp)

    def save_config(self):
        self.open_config()
        with open(self.config_fp, 'w') as cfg:
            self.config.write(cfg)

    def set_token_expiration(self):
        self.token_expiration = time.time() + token_validity

    def token_expired(self):
        return time.time() > self.token_expiration

    def refresh(self, force=False):
        if self.token_expired() or force:
            try:
                with self.loader(message='Refreshing token'):
                    new_access_info = self.reddit.refresh_access_information(
                        self.config['oauth']['refresh_token'])
                    self.access_info = new_access_info
                    self.reddit.set_access_credentials(scope=set(self.access_info['scope']),
                        access_token=self.access_info['access_token'],
                        refresh_token=self.access_info['refresh_token'])
                    self.set_token_expiration()
            except (praw.errors.OAuthAppRequired, praw.errors.OAuthInvalidToken) as e:
                show_notification(self.stdscr, ['Invalid OAuth data'])
            else:
                self.config['oauth']['access_token'] = self.access_info['access_token']
                self.config['oauth']['refresh_token'] = self.access_info['refresh_token']
                self.save_config()

    def authorize(self):
        self.reddit.set_oauth_app_info(self.client_id,
            self.client_secret,
            self.redirect_uri)

        self.open_config(update=True)
        # If no previous OAuth data found, starting from scratch
        if 'oauth' not in self.config or 'access_token' not in self.config['oauth']:
            # Generate a random UUID
            hex_uuid = uuid.uuid4().hex

            permission_ask_page_link = self.reddit.get_authorize_url(str(hex_uuid),
                scope=self.scope, refreshable=True)

            webbrowser.open(permission_ask_page_link)
            show_notification(self.stdscr, ['Access prompt opened in web browser'])

            final_state = prompt_input(self.stdscr, 'State: ')
            final_code = prompt_input(self.stdscr, 'Code: ')

            if not final_state or not final_code:
                curses.flash()
                return

            # Check if UUID matches obtained state
            # (if not, authorization process is compromised, and I'm giving up)
            if hex_uuid != final_state:
                show_notification(self.stdscr, ['UUID mismatch, stopping.'])
                return

            # Get access information (tokens and scopes)
            self.access_info = self.reddit.get_access_information(final_code)

            try:
                with self.loader(message='Logging in'):
                    self.reddit.set_access_credentials(
                        scope=set(self.access_info['scope']),
                        access_token=self.access_info['access_token'],
                        refresh_token=self.access_info['refresh_token'])
                    self.set_token_expiration()
            except (praw.errors.OAuthAppRequired, praw.errors.OAuthInvalidToken) as e:
                show_notification(self.stdscr, ['Invalid OAuth data'])
            else:
                if 'oauth' not in self.config:
                    self.config['oauth'] = {}

                self.config['oauth']['access_token'] = self.access_info['access_token']
                self.config['oauth']['refresh_token'] = self.access_info['refresh_token']
                self.save_config()
        # Otherwise, fetch new access token
        else:
            self.refresh(force=True)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import codecs
import argparse

from six.moves import configparser

from . import docs, __version__


HOME = os.path.expanduser('~')
PACKAGE = os.path.dirname(__file__)
XDG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
CONFIG = os.path.join(XDG_HOME, 'rtv', 'rtv.cfg')
TOKEN = os.path.join(XDG_HOME, 'rtv', 'refresh-token')
HISTORY = os.path.join(XDG_HOME, 'rtv', 'history.log')
TEMPLATE = os.path.join(PACKAGE, 'templates')


def build_parser():

    parser = argparse.ArgumentParser(
        prog='rtv', description=docs.SUMMARY,
        epilog=docs.CONTROLS+docs.HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-V', '--version', action='version', version='rtv '+__version__)
    parser.add_argument(
        '-s', dest='subreddit',
        help='name of the subreddit that will be opened on start')
    parser.add_argument(
        '-l', dest='link',
        help='full URL of a submission that will be opened on start')
    parser.add_argument(
        '--ascii', action='store_const', const=True,
        help='enable ascii-only mode')
    parser.add_argument(
        '--log', metavar='FILE', action='store',
        help='log HTTP requests to a file')
    parser.add_argument(
        '--non-persistent', dest='persistent', action='store_const',
        const=False,
        help='Forget all authenticated users when the program exits')
    parser.add_argument(
        '--clear-auth', dest='clear_auth', action='store_const', const=True,
        help='Remove any saved OAuth tokens before starting')
    return parser


class OrderedSet(object):
    """
    A simple implementation of an ordered set. A set is used to check
    for membership, and a list is used to maintain ordering.
    """

    def __init__(self, elements=None):
        elements = elements or []
        self._set = set(elements)
        self._list = elements

    def __contains__(self, item):
        return item in self._set

    def __len__(self):
        return len(self._list)

    def __getitem__(self, item):
        return self._list[item]

    def add(self, item):
        self._set.add(item)
        self._list.append(item)


class Config(object):

    DEFAULT = {
        'ascii': False,
        'persistent': True,
        'clear_auth': False,
        'log': None,
        'link': None,
        'subreddit': 'front',
        'history_size': 200,
        # https://github.com/reddit/reddit/wiki/OAuth2
        # Client ID is of type "installed app" and the secret should be empty
        'oauth_client_id': 'E2oEtRQfdfAfNQ',
        'oauth_client_secret': 'praw_gapfill',
        'oauth_redirect_uri': 'http://127.0.0.1:65000/',
        'oauth_redirect_port': 65000,
        'oauth_scope': [
            'edit', 'history', 'identity', 'mysubreddits', 'privatemessages',
            'read', 'report', 'save', 'submit', 'subscribe', 'vote'],
        'template_path': TEMPLATE,
    }

    def __init__(self,
                 config_file=CONFIG,
                 history_file=HISTORY,
                 token_file=TOKEN,
                 **kwargs):

        self.config_file = config_file
        self.history_file = history_file
        self.token_file = token_file
        self.config = kwargs

        # `refresh_token` and `history` are saved/loaded at separate locations,
        # so they are treated differently from the rest of the config options.
        self.refresh_token = None
        self.history = OrderedSet()

    def __getitem__(self, item):
        return self.config.get(item, self.DEFAULT.get(item))

    def __setitem__(self, key, value):
        self.config[key] = value

    def __delitem__(self, key):
        self.config.pop(key, None)

    def update(self, **kwargs):
        self.config.update(kwargs)

    def from_args(self):
        parser = build_parser()
        args = vars(parser.parse_args())
        # Filter out argument values that weren't supplied
        args = {key: val for key, val in args.items() if val is not None}
        self.update(**args)

    def from_file(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            with codecs.open(self.config_file, encoding='utf-8') as fp:
                config.readfp(fp)

        config_dict = {}
        if config.has_section('rtv'):
            config_dict = dict(config.items('rtv'))

        # Convert 'true'/'false' to boolean True/False
        if 'ascii' in config_dict:
            config_dict['ascii'] = config.getboolean('rtv', 'ascii')
        if 'clear_auth' in config_dict:
            config_dict['clear_auth'] = config.getboolean('rtv', 'clear_auth')
        if 'persistent' in config_dict:
            config_dict['persistent'] = config.getboolean('rtv', 'persistent')

        self.update(**config_dict)

    def load_refresh_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file) as fp:
                self.refresh_token = fp.read().strip()
        else:
            self.refresh_token = None

    def save_refresh_token(self):
        self._ensure_filepath(self.token_file)
        with open(self.token_file, 'w+') as fp:
            fp.write(self.refresh_token)

    def delete_refresh_token(self):
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        self.refresh_token = None

    def load_history(self):
        if os.path.exists(self.history_file):
            with codecs.open(self.history_file, encoding='utf-8') as fp:
                self.history = OrderedSet([line.strip() for line in fp])
        else:
            self.history = OrderedSet()

    def save_history(self):
        self._ensure_filepath(self.history_file)
        with codecs.open(self.history_file, 'w+', encoding='utf-8') as fp:
            fp.writelines('\n'.join(self.history[-self['history_size']:]))

    def delete_history(self):
        if os.path.exists(self.history_file):
            os.remove(self.history_file)
        self.history = OrderedSet()

    @staticmethod
    def _ensure_filepath(filename):
        """
        Ensure that the directory exists before trying to write to the file.
        """

        filepath = os.path.dirname(filename)
        if not os.path.exists(filepath):
            os.makedirs(filepath)
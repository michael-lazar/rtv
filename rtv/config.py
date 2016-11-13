# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import codecs
import shutil
import argparse
from functools import partial

import six
from six.moves import configparser

from . import docs, __version__
from .objects import KeyMap

PACKAGE = os.path.dirname(__file__)
HOME = os.path.expanduser('~')
TEMPLATES = os.path.join(PACKAGE, 'templates')
DEFAULT_CONFIG = os.path.join(TEMPLATES, 'rtv.cfg')
DEFAULT_MAILCAP = os.path.join(TEMPLATES, 'mailcap')
XDG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
CONFIG = os.path.join(XDG_HOME, 'rtv', 'rtv.cfg')
MAILCAP = os.path.join(HOME, '.mailcap')
TOKEN = os.path.join(XDG_HOME, 'rtv', 'refresh-token')
HISTORY = os.path.join(XDG_HOME, 'rtv', 'history.log')


def build_parser():

    parser = argparse.ArgumentParser(
        prog='rtv', description=docs.SUMMARY,
        epilog=docs.CONTROLS,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-V', '--version', action='version', version='rtv '+__version__)
    parser.add_argument(
        '-s', dest='subreddit',
        help='Name of the subreddit that will be opened on start')
    parser.add_argument(
        '-l', dest='link',
        help='Full URL of a submission that will be opened on start')
    parser.add_argument(
        '--log', metavar='FILE', action='store',
        help='Log HTTP requests to the given file')
    parser.add_argument(
        '--config', metavar='FILE', action='store',
        help='Load configuration settings from the given file')
    parser.add_argument(
        '--ascii', action='store_const', const=True,
        help='Enable ascii-only mode')
    parser.add_argument(
        '--monochrome', action='store_const', const=True,
        help='Disable color')
    parser.add_argument(
        '--non-persistent', dest='persistent', action='store_const',
        const=False,
        help='Forget the authenticated user when the program exits')
    parser.add_argument(
        '--clear-auth', dest='clear_auth', action='store_const', const=True,
        help='Remove any saved user data before launching')
    parser.add_argument(
        '--copy-config', dest='copy_config', action='store_const', const=True,
        help='Copy the default configuration to {HOME}/.config/rtv/rtv.cfg')
    parser.add_argument(
        '--copy-mailcap', dest='copy_mailcap', action='store_const', const=True,
        help='Copy an example mailcap configuration to {HOME}/.mailcap')
    parser.add_argument(
        '--enable-media', dest='enable_media', action='store_const', const=True,
        help='Open external links using programs defined in the mailcap config')
    return parser


def copy_default_mailcap(filename=MAILCAP):
    """
    Copy the example mailcap configuration to the specified file.
    """
    return _copy_settings_file(DEFAULT_MAILCAP, filename, 'mailcap')


def copy_default_config(filename=CONFIG):
    """
    Copy the default rtv user configuration to the specified file.
    """
    return _copy_settings_file(DEFAULT_CONFIG, filename, 'config')


def _copy_settings_file(source, destination, name):
    """
    Copy a file from the repo to the user's home directory.
    """

    if os.path.exists(destination):
        try:
            ch = six.moves.input(
                'File %s already exists, overwrite? y/[n]):' % destination)
            if ch not in ('Y', 'y'):
                return
        except KeyboardInterrupt:
            return

    filepath = os.path.dirname(destination)
    if not os.path.exists(filepath):
        os.makedirs(filepath)

    print('Copying default %s to %s' % (name, destination))
    shutil.copy(source, destination)
    os.chmod(destination, 0o664)


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

    def __init__(self, history_file=HISTORY, token_file=TOKEN, **kwargs):

        self.history_file = history_file
        self.token_file = token_file
        self.config = kwargs

        default, bindings = self.get_file(DEFAULT_CONFIG)
        self.default = default
        self.keymap = KeyMap(bindings)

        # `refresh_token` and `history` are saved/loaded at separate locations,
        # so they are treated differently from the rest of the config options.
        self.refresh_token = None
        self.history = OrderedSet()

    def __getitem__(self, item):
        if item in self.config:
            return self.config[item]
        else:
            return self.default.get(item, None)

    def __setitem__(self, key, value):
        self.config[key] = value

    def __delitem__(self, key):
        self.config.pop(key, None)

    def update(self, **kwargs):
        self.config.update(kwargs)

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
    def get_args():
        """
        Load settings from the command line.
        """

        parser = build_parser()
        args = vars(parser.parse_args())
        # Filter out argument values that weren't supplied
        return {key: val for key, val in args.items() if val is not None}

    @classmethod
    def get_file(cls, filename=None):
        """
        Load settings from an rtv configuration file.
        """

        if filename is None:
            filename = CONFIG

        config = configparser.ConfigParser()
        if os.path.exists(filename):
            with codecs.open(filename, encoding='utf-8') as fp:
                config.readfp(fp)

        return cls._parse_rtv_file(config)

    @staticmethod
    def _parse_rtv_file(config):

        rtv = {}
        if config.has_section('rtv'):
            rtv = dict(config.items('rtv'))

        params = {
            'ascii': partial(config.getboolean, 'rtv'),
            'monochrome': partial(config.getboolean, 'rtv'),
            'clear_auth': partial(config.getboolean, 'rtv'),
            'persistent': partial(config.getboolean, 'rtv'),
            'enable_media': partial(config.getboolean, 'rtv'),
            'history_size': partial(config.getint, 'rtv'),
            'oauth_redirect_port': partial(config.getint, 'rtv'),
            'oauth_scope': lambda x: rtv[x].split(','),
            'max_comment_cols': partial(config.getint, 'rtv'),
            'hide_username': partial(config.getboolean, 'rtv')
        }

        for key, func in params.items():
            if key in rtv:
                rtv[key] = func(key)

        bindings = {}
        if config.has_section('bindings'):
            bindings = dict(config.items('bindings'))

        for name, keys in bindings.items():
            bindings[name] = [key.strip() for key in keys.split(',')]

        return rtv, bindings

    @staticmethod
    def _ensure_filepath(filename):
        """
        Ensure that the directory exists before trying to write to the file.
        """

        filepath = os.path.dirname(filename)
        if not os.path.exists(filepath):
            os.makedirs(filepath)

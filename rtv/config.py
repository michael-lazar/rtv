"""
Global configuration settings
"""
import os
import argparse
from six.moves import configparser

from . import docs, __version__

HOME = os.path.expanduser('~')
XDG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
CONFIG = os.path.join(XDG_HOME, 'rtv', 'rtv.cfg')
TOKEN = os.path.join(XDG_HOME, 'rtv', 'refresh-token')

unicode = True
persistent = True

# https://github.com/reddit/reddit/wiki/OAuth2
# Client ID is of type "installed app" and the secret should be left empty
oauth_client_id = 'E2oEtRQfdfAfNQ'
oauth_client_secret = 'praw_gapfill'
oauth_redirect_uri = 'http://127.0.0.1:65000/'
oauth_redirect_port = 65000
oauth_scope = ['edit', 'history', 'identity', 'mysubreddits',
               'privatemessages', 'read', 'report', 'save', 'submit',
               'subscribe', 'vote']


def build_parser():
    parser = argparse.ArgumentParser(
        prog='rtv', description=docs.SUMMARY, epilog=docs.CONTROLS+docs.HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-V', '--version', action='version', version='rtv '+__version__,
    )
    parser.add_argument(
        '-s', dest='subreddit',
        help='name of the subreddit that will be opened on start')
    parser.add_argument(
        '-l', dest='link',
        help='full URL of a submission that will be opened on start')
    parser.add_argument(
        '--ascii', action='store_true',
        help='enable ascii-only mode')
    parser.add_argument(
        '--log', metavar='FILE', action='store',
        help='log HTTP requests to a file')
    parser.add_argument(
        '--non-persistent', dest='persistent', action='store_false',
        help='Forget all authenticated users when the program exits')
    parser.add_argument(
        '--clear-auth', dest='clear_auth', action='store_true',
        help='Remove any saved OAuth tokens before starting')
    return parser


def load_config():
    """
    Attempt to load settings from the local config file.
    """

    config = configparser.ConfigParser()
    if os.path.exists(CONFIG):
        config.read(CONFIG)

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

    return config_dict


def load_refresh_token(filename=TOKEN):
    if os.path.exists(filename):
        with open(filename) as fp:
            return fp.read().strip()
    else:
        return None


def save_refresh_token(token, filename=TOKEN):
    with open(filename, 'w+') as fp:
        fp.write(token)


def clear_refresh_token(filename=TOKEN):
    if os.path.exists(filename):
        os.remove(filename)

"""
Global configuration settings
"""
import os
from six.moves import configparser

HOME = os.path.expanduser('~')
XDG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
CONFIG = os.path.join(XDG_HOME, 'rtv', 'rtv.cfg')
TOKEN = os.path.join(XDG_HOME, 'rtv', 'refresh-token')

unicode = True
persistant = True

# https://github.com/reddit/reddit/wiki/OAuth2
# Client ID is of type "installed app" and the secret should be left empty
oauth_client_id = 'E2oEtRQfdfAfNQ'
oauth_client_secret = 'praw_gapfill'
oauth_redirect_uri = 'http://127.0.0.1:65000/'
oauth_redirect_port = 65000
oauth_scope = ['edit', 'history', 'identity', 'mysubreddits', 'privatemessages',
               'read', 'report', 'save', 'submit', 'subscribe', 'vote']

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
    if 'clear_session' in config_dict:
        config_dict['clear_session'] = config.getboolean('rtv', 'clear_session')
    if 'oauth_scope' in config_dict:
        config_dict['oauth_scope'] = config.oauth_scope.split('-')
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

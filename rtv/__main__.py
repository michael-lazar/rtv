import os
import sys
import argparse
import locale
import logging

import requests
import praw
import praw.errors
import configparser

from . import config
from .exceptions import SubmissionError, SubredditError, SubscriptionError, ProgramError
from .curses_helpers import curses_session, LoadScreen
from .submission import SubmissionPage
from .subreddit import SubredditPage
from .docs import *
from .oauth import OAuthTool
from .__version__ import __version__

__all__ = []

def open_config():
    """
    Search for a configuration file at the location ~/.rtv and attempt to load
    saved settings for things like the username and password.
    """

    config = configparser.ConfigParser()

    HOME = os.path.expanduser('~')
    XDG_CONFIG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
    config_paths = [
        os.path.join(XDG_CONFIG_HOME, 'rtv', 'rtv.cfg'),
        os.path.join(HOME, '.rtv')
    ]

    # read only the first existing config file
    for config_path in config_paths:
        if os.path.exists(config_path):
            config.read(config_path)
            break

    return config

def load_rtv_config():
    """
    Attempt to load saved settings for things like the username and password.
    """

    config = open_config()

    defaults = {}
    if config.has_section('rtv'):
        defaults = dict(config.items('rtv'))

    if 'ascii' in defaults:
        defaults['ascii'] = config.getboolean('rtv', 'ascii')

    return defaults

def load_oauth_config():
    """
    Attempt to load saved OAuth settings
    """

    config = open_config()

    defaults = {}
    if config.has_section('oauth'):
        defaults = dict(config.items('oauth'))

    return defaults

def command_line():

    parser = argparse.ArgumentParser(
        prog='rtv', description=SUMMARY,
        epilog=CONTROLS + HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-s', dest='subreddit', help='subreddit name')
    parser.add_argument('-l', dest='link', help='full link to a submission')
    parser.add_argument('--ascii', action='store_true',
                        help='enable ascii-only mode')
    parser.add_argument('--log', metavar='FILE', action='store',
                        help='Log HTTP requests')

    group = parser.add_argument_group('authentication (optional)', AUTH)
    group.add_argument('-u', dest='username', help='reddit username')
    group.add_argument('-p', dest='password', help='reddit password')

    oauth_group = parser.add_argument_group('OAuth data (optional)', OAUTH)
    oauth_group.add_argument('--auth-token', dest='authorization_token', help='OAuth authorization token')
    oauth_group.add_argument('--refresh-token', dest='refresh_token', help='OAuth refresh token')

    args = parser.parse_args()

    return args


def main():
    "Main entry point"

    # logging.basicConfig(level=logging.DEBUG, filename='rtv.log')
    locale.setlocale(locale.LC_ALL, '')

    args = command_line()
    local_rtv_config = load_rtv_config()
    local_oauth_config = load_oauth_config()

    # set the terminal title
    title = 'rtv {0}'.format(__version__)
    if os.name == 'nt':
        os.system('title {0}'.format(title))
    else:
        sys.stdout.write("\x1b]2;{0}\x07".format(title))

    # Fill in empty arguments with config file values. Paramaters explicitly
    # typed on the command line will take priority over config file params.
    for key, val in local_rtv_config.items():
        if getattr(args, key, None) is None:
            setattr(args, key, val)

    for k, v in local_oauth_config.items():
        if getattr(args, k, None) is None:
            setattr(args, k, v)

    config.unicode = (not args.ascii)

    # Squelch SSL warnings for Ubuntu
    logging.captureWarnings(True)
    if args.log:
        logging.basicConfig(level=logging.DEBUG, filename=args.log)

    try:
        print('Connecting...')
        reddit = praw.Reddit(user_agent=AGENT)
        reddit.config.decode_html_entities = False
        with curses_session() as stdscr:
            oauth = OAuthTool(reddit, stdscr, LoadScreen(stdscr))
            oauth.authorize()
            if args.link:
                page = SubmissionPage(stdscr, reddit, oauth, url=args.link)
                page.loop()
            subreddit = args.subreddit or 'front'
            page = SubredditPage(stdscr, reddit, oauth, subreddit)
            page.loop()
    except praw.errors.InvalidUserPass:
        print('Invalid password for username: {}'.format(args.username))
    except praw.errors.OAuthAppRequired:
        print('Invalid OAuth app config parameters')
    except requests.ConnectionError:
        print('Connection timeout')
    except requests.HTTPError:
        print('HTTP Error: 404 Not Found')
    except SubmissionError as e:
        print('Could not reach submission URL: {}'.format(e.url))
    except SubredditError as e:
        print('Could not reach subreddit: {}'.format(e.name))
    except ProgramError as e:
        print('Error: could not open file with program "{}", '
              'try setting RTV_EDITOR'.format(e.name))
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure sockets are closed to prevent a ResourceWarning
        reddit.handler.http.close()

sys.exit(main())

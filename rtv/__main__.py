import os
import sys
import argparse
import locale
import logging

import requests
import praw
import praw.errors
from six.moves import configparser

from . import config
from .exceptions import SubmissionError, SubredditError, ProgramError
from .curses_helpers import curses_session
from .submission import SubmissionPage
from .subreddit import SubredditPage
from .docs import *

__all__ = []

def load_config():
    """
    Search for a configuration file at the location ~/.rtv and attempt to load
    saved settings for things like the username and password.
    """

    config_path = os.path.join(os.path.expanduser('~'), '.rtv')
    config = configparser.ConfigParser()
    config.read(config_path)

    defaults = {}
    if config.has_section('rtv'):
        defaults = dict(config.items('rtv'))

    return defaults

def command_line():

    parser = argparse.ArgumentParser(
        prog='rtv', description=SUMMARY,
        epilog=CONTROLS+HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-s', dest='subreddit', help='subreddit name')
    parser.add_argument('-l', dest='link', help='full link to a submission')
    parser.add_argument('--unicode', action='store_true',
                        help='enable unicode (experimental)')
    parser.add_argument('--log', metavar='FILE', action='store',
                        help='Log HTTP requests')

    group = parser.add_argument_group('authentication (optional)', AUTH)
    group.add_argument('-u', dest='username', help='reddit username')
    group.add_argument('-p', dest='password', help='reddit password')

    args = parser.parse_args()

    return args

def main():
    "Main entry point"
    
    # logging.basicConfig(level=logging.DEBUG, filename='rtv.log')
    locale.setlocale(locale.LC_ALL, '')

    args = command_line()
    local_config = load_config()
    
    # Fill in empty arguments with config file values. Paramaters explicitly
    # typed on the command line will take priority over config file params.
    for key, val in local_config.items():
        if getattr(args, key, None) is None:
            setattr(args, key, val)

    config.unicode = args.unicode

    if args.log:
        logging.basicConfig(level=logging.DEBUG, filename=args.log)

    try:
        print('Connecting...')
        reddit = praw.Reddit(user_agent=AGENT)
        reddit.config.decode_html_entities = True
        if args.username:
            # PRAW will prompt for password if it is None
            reddit.login(args.username, args.password)
        with curses_session() as stdscr:
                if args.link:
                    page = SubmissionPage(stdscr, reddit, url=args.link)
                    page.loop()
                page = SubredditPage(stdscr, reddit, args.subreddit)
                page.loop()
    except praw.errors.InvalidUserPass:
        print('Invalid password for username: {}'.format(args.username))
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
        return

sys.exit(main())

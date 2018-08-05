# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position

from __future__ import unicode_literals
from __future__ import print_function

import os
import sys
import locale
import logging
import warnings

import six
import requests

# Need to check for curses compatibility before performing the rtv imports
try:
    import curses
except ImportError:
    if sys.platform == 'win32':
        sys.exit('Fatal Error: This program is not compatible with Windows '
                 'Operating Systems.\nPlease try installing on either Linux '
                 'or Mac OS')
    else:
        sys.exit('Fatal Error: Your python distribution appears to be missing '
                 '_curses.so.\nWas it compiled without support for curses?')

# If we want to override the $BROWSER variable that the python webbrowser
# references, it needs to be done before the webbrowser module is imported
# for the first time.
webbrowser_import_warning = ('webbrowser' in sys.modules)
RTV_BROWSER, BROWSER = os.environ.get('RTV_BROWSER'), os.environ.get('BROWSER')
if RTV_BROWSER:
    os.environ['BROWSER'] = RTV_BROWSER

from . import docs
from . import packages
from .packages import praw
from .config import Config, copy_default_config, copy_default_mailcap
from .theme import Theme
from .oauth import OAuthHelper
from .terminal import Terminal
from .content import RequestHeaderRateLimiter
from .objects import curses_session, patch_webbrowser
from .subreddit_page import SubredditPage
from .exceptions import ConfigError, SubredditError
from .__version__ import __version__

_logger = logging.getLogger(__name__)


# Pycharm debugging note:
# You can use pycharm to debug a curses application by launching rtv in a
# console window (python -m rtv) and using pycharm to attach to the remote
# process. On Ubuntu, you may need to allow ptrace permissions by setting
# ptrace_scope to 0 in /etc/sysctl.d/10-ptrace.conf.
# http://blog.mellenthin.de/archives/2010/10/18/gdb-attach-fails


def main():
    """Main entry point"""

    config, user_agent = initialize()
    if not config:
        return

    try:
        with curses_session() as stdscr:
            term = Terminal(stdscr, config)
            run(config, user_agent, term)
    except ConfigError as e:
        _logger.exception(e)
        print(e)
    except Exception as e:
        _logger.exception(e)
        raise
    except KeyboardInterrupt:
        pass
    finally:
        # Try to save the browsing history
        config.save_history()
        # Ensure sockets are closed to prevent a ResourceWarning
        if 'reddit' in locals():
            reddit.handler.http.close()


def initialize():
    squelch_SSL_warnings()
    set_terminal_title()

    config = get_config()
    if handle_special_arguments(config):
        return False
    config.load_history()
    config.load_refresh_token()
    if config['clear_auth']:
        config.delete_refresh_token()

    set_up_logging(config)
    ensure_utf8_or_fall_back_to_ascii(config)
    _logger.info('RTV module path: %s', os.path.abspath(__file__))
    check_praw_version()
    update_webbrowser_module_default_behavoir()

    user_agent = docs.AGENT.format(version=__version__)

    return config, user_agent


def squelch_SSL_warnings():
    logging.captureWarnings(True)
    if six.PY3:
        # These ones get triggered even when capturing warnings is turned on
        warnings.simplefilter('ignore', ResourceWarning)  # pylint:disable=E0602


def set_terminal_title():
    if os.getenv('DISPLAY'):
        title = 'rtv {0}'.format(__version__)
        sys.stdout.write('\x1b]2;{0}\x07'.format(title))
        sys.stdout.flush()


def get_config():
    args = Config.get_args()
    fargs, bindings = Config.get_file(args.get('config'))

    # Apply the file config first, then overwrite with any command line args
    config = Config()
    config.update(**fargs)
    config.update(**args)

    # If key bindings are supplied in the config file, overwrite the defaults
    if bindings:
        config.keymap.set_bindings(bindings)

    return config


def handle_special_arguments(config):
    if config['copy_config']:
        copy_default_config()
        return True
    if config['copy_mailcap']:
        copy_default_mailcap()
        return True
    if config['list_themes']:
        Theme.print_themes()
        return True
    return False


def set_up_logging(config):
    if config['log']:
        # Log request headers to the file (print hack only works on python 3.x)
        # from http import client
        # _http_logger = logging.getLogger('http.client')
        # client.HTTPConnection.debuglevel = 2
        # def print_to_file(*args, **_):
        #     if args[0] != "header:":
        #         _http_logger.info(' '.join(args))
        # client.print = print_to_file
        logging.basicConfig(
            level=logging.DEBUG,
            filename=config['log'],
            format='%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s')
        _logger.info('Starting new session, RTV v%s', __version__)
        _logger.info('%s, %s', sys.executable, sys.version)
        env = [
            ('$DISPLAY', os.getenv('DISPLAY')),
            ('$TERM', os.getenv('TERM')),
            ('$XDG_CONFIG_HOME', os.getenv('XDG_CONFIG_HOME')),
            ('$XDG_DATA_HOME', os.getenv('$XDG_DATA_HOME')),
            ('$RTV_EDITOR', os.getenv('RTV_EDITOR')),
            ('$RTV_URLVIEWER', os.getenv('RTV_URLVIEWER')),
            ('$RTV_BROWSER', RTV_BROWSER),
            ('$BROWSER', BROWSER),
            ('$RTV_PAGER', os.getenv('RTV_PAGER')),
            ('$PAGER', os.getenv('PAGER')),
            ('$VISUAL', os.getenv('VISUAL')),
            ('$EDITOR', os.getenv('EDITOR'))]
        _logger.info('Environment: %s', env)
    else:
        # Add an empty handler so the logger doesn't complain
        logging.root.addHandler(logging.NullHandler())


def ensure_utf8_or_fall_back_to_ascii(config):
    default_locale = locale.setlocale(locale.LC_ALL, '')
    try:
        encoding = locale.getlocale()[1] or locale.getdefaultlocale()[1]
    except ValueError:
        # http://stackoverflow.com/a/19961403
        # OS X on some terminals will set the LC_CTYPE to "UTF-8"
        # (as opposed to something like "en_US.UTF-8") and python
        # doesn't know how to handle it.
        _logger.warning('Error parsing system locale: `%s`,'
                        ' falling back to utf-8', default_locale)
        encoding = 'UTF-8'

    if not encoding or encoding.lower() != 'utf-8':
        text = ('System encoding was detected as (%s) instead of UTF-8'
                ', falling back to ascii only mode' % encoding)
        warnings.warn(text)
        config['ascii'] = True


def check_praw_version():
    if packages.__praw_bundled__:
        _logger.info('Using packaged PRAW distribution, '
                     'commit %s', packages.__praw_hash__)
    else:
        _logger.info('Packaged PRAW not found, falling back to system '
                     'installed version %s', praw.__version__)


def update_webbrowser_module_default_behavoir():
    patch_webbrowser()
    if webbrowser_import_warning:
        _logger.warning('webbrowser module was unexpectedly imported before'
                        '$BROWSER could be overwritten')


def run(config, user_agent, term):
    set_terminal_theme(term, config)
    reddit = get_reddit(term, user_agent)
    oauth = authorize_if_possible(reddit, term, config)

    page = get_subreddit_page(config, term, reddit, oauth)
    if page is None:
        return

    open_submission_link_if_supplied(config, reddit, page)

    page.loop()


def set_terminal_theme(term, config):
    if config['monochrome'] or config['theme'] == 'monochrome':
        _logger.info('Using monochrome theme')
        theme = Theme(use_color=False)
    elif config['theme'] and config['theme'] != 'default':
        _logger.info('Loading theme: %s', config['theme'])
        theme = Theme.from_name(config['theme'])
    else:
        # Set to None to let the terminal figure out which theme to use
        # depending on if colors are supported or not
        theme = None
    term.set_theme(theme)


def get_reddit(term, user_agent):
    with term.loader('Initializing', catch_exception=False):
        reddit = praw.Reddit(user_agent=user_agent,
                             decode_html_entities=False,
                             disable_update_check=True,
                             timeout=10,  # 10 second request timeout
                             handler=RequestHeaderRateLimiter())

    # Dial the request cache up from 30 seconds to 5 minutes
    # I'm trying this out to make navigation back and forth between pages
    # quicker, it may still need to be fine tuned.
    reddit.config.api_request_delay = 300

    return reddit


def authorize_if_possible(reddit, term, config):
    oauth = OAuthHelper(reddit, term, config)
    if config.refresh_token:
        oauth.authorize()
    return oauth


def get_subreddit_page(config, term, reddit, oauth):
    page = None
    name = config['subreddit']
    with term.loader('Loading subreddit'):
        try:
            page = SubredditPage(reddit, term, config, oauth, name)
        except Exception as e:
            # If we can't load the subreddit that was requested, try to load
            # the front page instead so at least the application still
            # launches.
            _logger.exception(e)
            page = SubredditPage(reddit, term, config, oauth, 'front')
            raise SubredditError('Unable to load {0}'.format(name))
    return page


def open_submission_link_if_supplied(config, reddit, page):
    if config['link']:
        # Expand shortened urls like https://redd.it/
        # Praw won't accept the shortened versions, add the reddit headers to
        # avoid a 429 response from reddit.com
        url = requests.head(config['link'], headers=reddit.http.headers,
                            allow_redirects=True).url

        page.open_submission(url=url)


sys.exit(main())

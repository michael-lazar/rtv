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
                 'Operating Systems.')
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
from .submission_page import SubmissionPage
from .exceptions import ConfigError, SubredditError, SubmissionError
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

    # Squelch SSL warnings
    logging.captureWarnings(True)
    if six.PY3:
        # These ones get triggered even when capturing warnings is turned on
        warnings.simplefilter('ignore', ResourceWarning)  # pylint:disable=E0602

    # Set the terminal title
    if os.getenv('DISPLAY'):
        title = 'rtv {0}'.format(__version__)
        sys.stdout.write('\x1b]2;{0}\x07'.format(title))
        sys.stdout.flush()

    args = Config.get_args()
    fargs, bindings = Config.get_file(args.get('config'))

    # Apply the file config first, then overwrite with any command line args
    config = Config()
    config.update(**fargs)
    config.update(**args)

    # If key bindings are supplied in the config file, overwrite the defaults
    if bindings:
        config.keymap.set_bindings(bindings)

    if config['copy_config']:
        return copy_default_config()
    if config['copy_mailcap']:
        return copy_default_mailcap()
    if config['list_themes']:
        return Theme.print_themes()

    # Load the browsing history from previous sessions
    config.load_history()

    # Load any previously saved auth session token
    config.load_refresh_token()
    if config['clear_auth']:
        config.delete_refresh_token()

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
    else:
        # Add an empty handler so the logger doesn't complain
        logging.root.addHandler(logging.NullHandler())

    # Make sure the locale is UTF-8 for unicode support
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

    if packages.__praw_bundled__:
        praw_info = 'packaged, commit {}'.format(packages.__praw_hash__[:12])
    else:
        praw_info = 'system installed v{}'.format(praw.__version__)

    # Update the webbrowser module's default behavior
    patch_webbrowser()
    if webbrowser_import_warning:
        _logger.warning('webbrowser module was unexpectedly imported before'
                        '$BROWSER could be overwritten')

    # Construct the reddit user agent
    user_agent = docs.AGENT.format(version=__version__)

    debug_info = [
        'rtv version: rtv {}'.format(__version__),
        'rtv module path: {}'.format(os.path.abspath(__file__)),
        'python version: {}'.format(sys.version.replace('\n', ' ')),
        'python executable: {}'.format(sys.executable),
        'praw version: {}'.format(praw_info),
        'locale, encoding: {}, {}'.format(default_locale, encoding),
        'Environment Variables']
    for name, value in [
        ('BROWSER', BROWSER),
        ('DISPLAY', os.getenv('DISPLAY')),
        ('EDITOR', os.getenv('EDITOR')),
        ('LANG', os.getenv('LANG')),
        ('PAGER', os.getenv('PAGER')),
        ('RTV_BROWSER', RTV_BROWSER),
        ('RTV_EDITOR', os.getenv('RTV_EDITOR')),
        ('RTV_PAGER', os.getenv('RTV_PAGER')),
        ('RTV_URLVIEWER', os.getenv('RTV_URLVIEWER')),
        ('TERM', os.getenv('TERM')),
        ('VISUAL', os.getenv('VISUAL')),
        ('XDG_CONFIG_HOME', os.getenv('XDG_CONFIG_HOME')),
        ('XDG_DATA_HOME', os.getenv('XDG_DATA_HOME')),
    ]:
        debug_info.append('  {:<16}: {}'.format(name, value or ''))
    debug_info.append('')
    debug_text = '\n'.join(debug_info)

    _logger.info(debug_text)
    if config['debug_info']:
        print(debug_text)
        return

    try:
        with curses_session() as stdscr:

            term = Terminal(stdscr, config)

            if config['monochrome'] or config['theme'] == 'monochrome':
                _logger.info('Using monochrome theme')
                theme = Theme(use_color=False)
            elif config['theme'] and config['theme'] != 'default':
                _logger.info('Loading theme: %s', config['theme'])
                theme = Theme.from_name(config['theme'])
            else:
                # Set to None to let the terminal figure out which theme
                # to use depending on if colors are supported or not
                theme = None
            term.set_theme(theme)

            with term.loader('Initializing', catch_exception=False):
                reddit = praw.Reddit(user_agent=user_agent,
                                     decode_html_entities=False,
                                     disable_update_check=True,
                                     timeout=10,  # 10 second request timeout
                                     handler=RequestHeaderRateLimiter())

            # Dial the request cache up from 30 seconds to 5 minutes
            # I'm trying this out to make navigation back and forth
            # between pages quicker, it may still need to be fine tuned.
            reddit.config.api_request_delay = 300

            # Authorize on launch if the refresh token is present
            oauth = OAuthHelper(reddit, term, config)
            if config['autologin'] and config.refresh_token:
                oauth.authorize(autologin=True)

            # Open the supplied submission link before opening the subreddit
            if config['link']:
                # Expand shortened urls like https://redd.it/
                # Praw won't accept the shortened versions, add the reddit
                # headers to avoid a 429 response from reddit.com
                url = requests.head(
                    config['link'],
                    headers=reddit.http.headers,
                    allow_redirects=True
                ).url

                page = None
                with term.loader('Loading submission'):
                    try:
                        page = SubmissionPage(reddit, term, config, oauth, url)
                    except Exception as e:
                        _logger.exception(e)
                        raise SubmissionError('Unable to load {0}'.format(url))
                while page:
                    page = page.loop()

            page = None
            name = config['subreddit']
            with term.loader('Loading subreddit'):
                try:
                    page = SubredditPage(reddit, term, config, oauth, name)
                except Exception as e:
                    # If we can't load the subreddit that was requested, try
                    # to load the "popular" page instead so at least the
                    # application still launches. This used to use the user's
                    # front page, but some users have an empty front page.
                    _logger.exception(e)
                    page = SubredditPage(reddit, term, config, oauth, 'popular')
                    raise SubredditError('Unable to load {0}'.format(name))

            # Launch the subreddit page
            while page:
                page = page.loop()

    except ConfigError as e:
        _logger.exception(e)
        print(e)
    except Exception as e:
        _logger.exception(e)
        import traceback
        exit_message = '\n'.join([
            debug_text,
            traceback.format_exc(),
            'rtv has crashed. Please report this traceback at:',
            'https://github.com/michael-lazar/rtv/issues\n'])
        sys.stderr.write(exit_message)
        return 1  # General error exception code
    except KeyboardInterrupt:
        pass
    finally:
        # Try to save the browsing history
        config.save_history()
        # Ensure sockets are closed to prevent a ResourceWarning
        if 'reddit' in locals():
            reddit.handler.http.close()


sys.exit(main())

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import locale
import logging

import praw
import tornado

from . import docs
from .config import Config, copy_default_config
from .oauth import OAuthHelper
from .terminal import Terminal
from .objects import curses_session, Color
from .subreddit import SubredditPage
from .exceptions import ConfigError
from .__version__ import __version__


_logger = logging.getLogger(__name__)

# Pycharm debugging note:
# You can use pycharm to debug a curses application by launching rtv in a
# console window (python -m rtv) and using pycharm to attach to the remote
# process. On Ubuntu, you may need to allow ptrace permissions by setting
# ptrace_scope to 0 in /etc/sysctl.d/10-ptrace.conf.
# http://blog.mellenthin.de/archives/2010/10/18/gdb-attach-fails


def main():
    "Main entry point"

    # Squelch SSL warnings
    logging.captureWarnings(True)
    locale.setlocale(locale.LC_ALL, '')

    # Set the terminal title
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

    # Copy the default config file and quit
    if config['copy_config']:
        copy_default_config()
        return

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
        _logger.info('Starting new session, RTV v%s', __version__)
    else:
        # Add an empty handler so the logger doesn't complain
        logging.root.addHandler(logging.NullHandler())

    # Construct the reddit user agent
    user_agent = docs.AGENT.format(version=__version__)

    try:
        with curses_session() as stdscr:

            # Initialize global color-pairs with curses
            if not config['monochrome']:
                Color.init()

            term = Terminal(stdscr, config['ascii'])
            with term.loader('Initializing', catch_exception=False):
                reddit = praw.Reddit(user_agent=user_agent,
                                     decode_html_entities=False,
                                     disable_update_check=True)

            # Authorize on launch if the refresh token is present
            oauth = OAuthHelper(reddit, term, config)
            if config.refresh_token:
                oauth.authorize()

            name = config['subreddit']
            with term.loader('Loading subreddit'):
                page = SubredditPage(reddit, term, config, oauth, name)
            if term.loader.exception:
                return

            # Open the supplied submission link before opening the subreddit
            if config['link']:
                page.open_submission(url=config['link'])

            # Launch the subreddit page
            page.loop()

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
        # Explicitly close file descriptors opened by Tornado's IOLoop
        tornado.ioloop.IOLoop.current().close(all_fds=True)

sys.exit(main())

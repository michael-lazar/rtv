import os
import sys
import locale
import logging
import signal

import requests
import praw
import praw.errors
import tornado

from . import config
from .exceptions import SubmissionError, SubredditError, SubscriptionError, ProgramError
from .curses_helpers import curses_session, KeyboardInterruptible, LoadScreen
from .submission import SubmissionPage
from .subreddit import SubredditPage
from .docs import AGENT
from .oauth import OAuthTool
from .__version__ import __version__

__all__ = []

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
    if os.name == 'nt':
        os.system('title {0}'.format(title))
    else:
        sys.stdout.write("\x1b]2;{0}\x07".format(title))

    # Fill in empty arguments with config file values. Parameters explicitly
    # typed on the command line will take priority over config file params.
    parser = config.build_parser()
    args = parser.parse_args()

    local_config = config.load_config()
    for key, val in local_config.items():
        if getattr(args, key, None) is None:
            setattr(args, key, val)

    if args.ascii:
        config.unicode = False
    if not args.persistent:
        config.persistent = False
    if args.log:
        logging.basicConfig(level=logging.DEBUG, filename=args.log)
    if args.clear_auth:
        config.clear_refresh_token()

    try:
        print('Connecting...')
        reddit = praw.Reddit(user_agent=AGENT.format(version=__version__))
        reddit.config.decode_html_entities = False
        KeyboardInterruptible.ignore_interrupt()

        def loop(stdscr):
            oauth = OAuthTool(reddit, stdscr, LoadScreen(stdscr))
            if oauth.refresh_token:
                oauth.authorize()

            with KeyboardInterruptible(stdscr) as k:
                if args.link:
                    page = SubmissionPage(stdscr, reddit, oauth, url=args.link)
                else:
                    page = SubredditPage(stdscr, reddit, oauth, args.subreddit)
                k.disable()
                page.loop()

        curses_session(loop)
    except requests.exceptions.RequestException:
        print('Request failed')
    except (praw.errors.OAuthAppRequired, praw.errors.OAuthInvalidToken):
        print('Invalid OAuth data')
    except praw.errors.NotFound:
        print('HTTP Error: 404 Not Found')
    except praw.errors.HTTPException:
        print('Connection timeout')
    except SubmissionError as e:
        print('Could not reach submission URL: {}'.format(e.url))
    except SubredditError as e:
        print('Could not reach subreddit: {}'.format(e.name))
    except ProgramError as e:
        print('Error: could not open file with program "{}", '
              'try setting RTV_EDITOR'.format(e.name))
    finally:
        # Ensure sockets are closed to prevent a ResourceWarning
        reddit.handler.http.close()
        # Explicitly close file descriptors opened by Tornado's IOLoop
        tornado.ioloop.IOLoop.current().close(all_fds=True)

sys.exit(main())

import argparse
import praw
from requests.exceptions import ConnectionError, HTTPError

from rtv.errors import SubmissionURLError, SubredditNameError
from rtv.utils import curses_session
from rtv.subreddit import SubredditPage
from rtv.submission import SubmissionPage

description = """
Reddit Terminal Viewer is a lightweight browser for www.reddit.com built into a
terminal window.
"""

epilog = """
controls:
  arrow keys    navigate submissions and open comments
  q             quit
  F5            refresh the page
  /             open a prompt to switch subreddits
"""

def main():

    parser = argparse.ArgumentParser(
        prog='rtv', description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', dest='subreddit', default='front', help='subreddit name')
    parser.add_argument('-l', dest='link', help='full link to a submission')

    group = parser.add_argument_group('authentication (optional)')
    group.add_argument('-u', dest='username', help='reddit username')
    group.add_argument('-p', dest='password', help='reddit password')

    args = parser.parse_args()

    try:
        reddit = praw.Reddit(user_agent='reddit terminal viewer v0.0')
        reddit.config.decode_html_entities = True

        if args.username and args.password:
            reddit.login(args.username, args.password)

        with curses_session() as stdscr:

                if args.link:
                    page = SubmissionPage(stdscr, reddit, url=args.link)
                    page.loop()

                page = SubredditPage(stdscr, reddit, args.subreddit)
                page.loop()

    except KeyboardInterrupt:
        return

    except ConnectionError:
        print('Timeout: Could not connect to website')

    except HTTPError:
        print('HTTP Error: 404 Not Found')

    except SubmissionURLError as e:
        print('Could not reach submission URL: {}'.format(e.url))

    except SubredditNameError as e:
        print('Could not reach subreddit: {}'.format(e.name))


if __name__ == '__main__':
    main()
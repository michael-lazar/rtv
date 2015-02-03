import argparse
import praw
from requests.exceptions import ConnectionError

from errors import SubmissionURLError, SubredditNameError
from utils import curses_session
from subreddit import SubredditPage
from submission import SubmissionPage

parser = argparse.ArgumentParser(description='Reddit Terminal Viewer')
parser.add_argument('-s', dest='subreddit', default='front', help='subreddit name')
parser.add_argument('-l', dest='link', help='full link to a submission')

group = parser.add_argument_group('authentication (optional)')
group.add_argument('-u', dest='username', help='reddit username')
group.add_argument('-p', dest='password', help='reddit password')

def main():

    args = parser.parse_args()

    try:
        reddit = praw.Reddit(user_agent='reddit terminal viewer v0.0')
        reddit.config.decode_html_entities = True

        if args.username and args.password:
            reddit.login(args.username, args.password)

        with curses_session() as stdscr:

                if args.link:
                    # Go directly to submission
                    page = SubmissionPage(stdscr, reddit, url=args.link)
                    page.loop()

                page = SubredditPage(stdscr, reddit, args.subreddit)
                page.loop()

    except KeyboardInterrupt:
        return

    except ConnectionError:
        print 'Timeout: Could not connect to website'

    except SubmissionURLError as e:
        print 'Could not reach submission URL: {}'.format(e.url)

    except SubredditNameError as e:
        print 'Could not reach subreddit: {}'.format(e.name)


if __name__ == '__main__':
    main()

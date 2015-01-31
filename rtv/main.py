import argparse
import praw
from utils import curses_session, LoadScreen
from content import SubredditContent
from subreddit import SubredditPage

parser = argparse.ArgumentParser(description='Reddit Terminal Viewer')
parser.add_argument('-s', dest='subreddit', default='front', help='subreddit name')
parser.add_argument('-l', dest='link', help='full link to a specific submission')
group = parser.add_argument_group('authentication (optional)')
group.add_argument('-u', dest='username', help='reddit username')
group.add_argument('-p', dest='password', help='reddit password')

def main(args):

    r = praw.Reddit(user_agent='reddit terminal viewer v0.0')
    r.config.decode_html_entities = True

    if args.username and args.password:
        r.login(args.username, args.password)

    with curses_session() as stdscr:

        loader = LoadScreen(stdscr)
        content = SubredditContent(r, subreddit=args.subreddit, loader=loader)
        page = SubredditPage(stdscr, content)
        page.loop()

if __name__ == '__main__':

    args = parser.parse_args()
    main(args)
import argparse
import praw
from utils import curses_session
from content_generators import SubredditContent
from subreddit_viewer import SubredditViewer

parser = argparse.ArgumentParser(description='Reddit Terminal Viewer (RTV)')
parser.add_argument('-u', '--username', help='reddit username')
parser.add_argument('-p', '--password', help='reddit password')
parser.add_argument('-s', '--subreddit', default='front', help='subreddit name')
parser.add_argument('-l', '--link', help='full link to a specific submission')

def main(args):

    r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
    if args.username and args.password:
        r.login(args.username, args.password)

    with curses_session() as stdscr:

        content = SubredditContent(r, subreddit=args.subreddit)
        viewer = SubredditViewer(stdscr, content)
        viewer.loop()

if __name__ == '__main__':

    args = parser.parse_args()
    main(args)
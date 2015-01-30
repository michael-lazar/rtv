import argparse
import praw
from utils import curses_session
from content import SubredditContainer
from subreddit_viewer import SubredditViewer

parser = argparse.ArgumentParser(description='Reddit Terminal Viewer')
parser.add_argument('-s', dest='subreddit', default='front', help='subreddit name')
parser.add_argument('-l', dest='link', help='full link to a specific submission')
group = parser.add_argument_group('authentication (optional)')
group.add_argument('-u', dest='username', help='reddit username')
group.add_argument('-p', dest='password', help='reddit password')

def main(args):

    r = praw.Reddit(user_agent='reddit terminal viewer v0.0')
    if args.username and args.password:
        r.login(args.username, args.password)

    with curses_session() as stdscr:

        content = SubredditContainer(r, subreddit=args.subreddit)
        viewer = SubredditViewer(stdscr, content)
        viewer.loop()

if __name__ == '__main__':

    args = parser.parse_args()
    main(args)
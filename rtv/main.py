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

# TODO: Figure out a way to sync this with the README
epilog = """
Usage
-----
RTV currently supports browsing both subreddits and individual submissions.
In each mode the controls are slightly different. In subreddit mode you can 
browse through the top submissions on either the front page or a specific 
subreddit. In submission mode you can view the self text for a submission and 
browse comments.

Global Commands
  Arrow Keys or `hjkl`: RTV supports both the arrow keys and vim bindings for
                        navigation. Move up and down to scroll through items
                        on the page.
  `r` or `F5`         : Refresh the current page.
  `q`                 : Quit the program.

Subreddit Mode
  Right or `Enter`    : Open the currently selected submission in a new page.
  `/`                 : Open a prompt to switch to a different subreddit. For
                        example, pressing `/` and typing "python" will open
                        "/r/python". You can return to Reddit's front page
                        by using the alias "/r/front".

Submission Mode
  Right or `Enter`    : Toggle the currently selected comment between hidden
                        and visible. Alternatively, load addition comments
                        identified by "[+] more comments".
  Left                : Exit the submission page and return to the subreddit.
"""

def main():

    parser = argparse.ArgumentParser(
        prog='rtv', description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', dest='subreddit', default='front', help='subreddit name')
    parser.add_argument('-l', dest='link', help='full link to a submission')

    group = parser.add_argument_group(
        'authentication (optional)', 
        'Authenticating allows you to view your customized front page. '
        'If only the username is given, the password will be prompted '
        'securely.')
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

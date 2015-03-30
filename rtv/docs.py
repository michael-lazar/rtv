from .__version__ import __version__

__all__ = ['AGENT', 'SUMMARY', 'AUTH', 'CONTROLS', 'HELP']

AGENT = """
desktop:https://github.com/michael-lazar/rtv:{} (by /u/civilization_phaze_3)
""".format(__version__)

SUMMARY = """
Reddit Terminal Viewer is a lightweight browser for www.reddit.com built into a
terminal window.
"""

AUTH = """\
Authenticating is required to vote and leave comments. If only a username is
given, the program will display a secure prompt to enter a password.
"""

CONTROLS = """
Controls
--------
RTV currently supports browsing both subreddits and individual submissions.
In each mode the controls are slightly different. In subreddit mode you can
browse through the top submissions on either the front page or a specific
subreddit. In submission mode you can view the self text for a submission and
browse comments.
"""

HELP = """
Global Commands
  `UP/DOWN` or `j/k`  : Scroll to the prev/next item
  `a/z`               : Upvote/downvote the selected item
  `r`                 : Refresh the current page
  `q`                 : Quit the program
  `o`                 : Open the selected item in the default web browser
  `?`                 : Show this help message

Subreddit Mode
  `RIGHT` or `l`      : View comments for the selected submission
  `/`                 : Open a prompt to switch subreddits

Submission Mode
  `LEFT` or `h`       : Return to subreddit mode
  `RIGHT` or `l`      : Fold the selected comment, or load additional comments
  `c`                 : Comment/reply on the selected item 
"""

COMMENT_FILE = """
# Please enter a comment. Lines starting with '#' will be ignored,
# and an empty message aborts the comment.
#
# Replying to {author}'s {type}
{content}
"""

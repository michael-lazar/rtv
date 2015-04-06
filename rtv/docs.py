from .__version__ import __version__

__all__ = ['AGENT', 'SUMMARY', 'AUTH', 'CONTROLS', 'HELP', 'COMMENT_FILE',
           'SUBMISSION_FILE']

AGENT = """\
desktop:https://github.com/michael-lazar/rtv:{} (by /u/civilization_phaze_3)\
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
  `ENTER` or `o`      : Open the selected item in the default web browser
  `r`                 : Refresh the current page
  `u`                 : Login/logout of your user account
  `?`                 : Show this help message
  `q`                 : Quit the program

Subreddit Mode
  `RIGHT` or `l`      : View comments for the selected submission
  `/`                 : Open a prompt to switch subreddits
  `f`                 : Open a prompt to search the current subreddit
  `p`                 : Post a new submission to the current subreddit

Submission Mode
  `LEFT` or `h`       : Return to subreddit mode
  `RIGHT` or `l`      : Fold the selected comment, or load additional comments
  `c`                 : Post a new comment on the selected item
"""

COMMENT_FILE = """
# Please enter a comment. Lines starting with '#' will be ignored,
# and an empty message aborts the comment.
#
# Replying to {author}'s {type}
{content}
"""

SUBMISSION_FILE = """
# Please enter your submission. Lines starting with '#' will be ignored,
# and an empty field aborts the submission.
#
# The first line will be interpreted as the title
# The following lines will be interpreted as the content
#
# Posting to /r/{name}
"""
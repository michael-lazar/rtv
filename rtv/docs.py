__all__ = ['AGENT', 'SUMMARY', 'CONTROLS', 'HELP', 'COMMENT_FILE',
           'SUBMISSION_FILE', 'COMMENT_EDIT_FILE']

AGENT = """\
desktop:https://github.com/michael-lazar/rtv:{version}\
(by /u/civilization_phaze_3)\
"""

SUMMARY = """
Reddit Terminal Viewer is a lightweight browser for www.reddit.com built into a
terminal window.
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
Basic Commands
  `j/k` or `UP/DOWN`  : Move the cursor up/down
  `m/n` or `PgUp/PgDn`: Jump to the previous/next page
  `o` or `ENTER`      : Open the selected item as a webpage
  `r` or `F5`         : Refresh page content
  `u`                 : Log in or switch accounts
  `?`                 : Show the help screen
  `q/Q`               : Quit/Force quit

Authenticated Commands
  `a/z`               : Upvote/downvote
  `c`                 : Compose a new post or comment
  `e`                 : Edit an existing post or comment
  `d`                 : Delete an existing post or comment
  `i`                 : Display new messages prompt
  `s`                 : Open/close subscribed subreddits list

Subreddit Mode
  `l` or `RIGHT`      : Enter the selected submission
  `/`                 : Open a prompt to switch subreddits
  `f`                 : Open a prompt to search the current subreddit

Submission Mode
  `h` or `LEFT`       : Return to subreddit mode
  `SPACE`             : Fold the selected comment, or load additional comments
"""

COMMENT_FILE = u"""
# Please enter a comment. Lines starting with '#' will be ignored,
# and an empty message aborts the comment.
#
# Replying to {author}'s {type}
{content}
"""

COMMENT_EDIT_FILE = u"""{content}
# Please enter a comment. Lines starting with '#' will be ignored,
# and an empty message aborts the comment.
#
# Editing your comment
"""

SUBMISSION_FILE = u"""{content}
# Please enter your submission. Lines starting with '#' will be ignored,
# and an empty field aborts the submission.
#
# The first line will be interpreted as the title
# The following lines will be interpreted as the content
#
# Posting to {name}
"""

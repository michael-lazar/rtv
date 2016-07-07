# -*- coding: utf-8 -*-
from __future__ import unicode_literals

AGENT = """\
desktop:https://github.com/michael-lazar/rtv:{version}\
(by /u/civilization_phaze_3)\
"""

SUMMARY = """
Reddit Terminal Viewer is a lightweight browser for www.reddit.com built into a
terminal window.
"""

CONTROLS = """
Move the cursor using either the arrow keys or *Vim* style movement.
Press `?` to open the help screen.
"""

HELP = """
[Basic Commands]
  `j/k` or `UP/DOWN`  : Move the cursor up/down
  `m/n` or `PgUp/PgDn`: Jump to the previous/next page
  `o` or `ENTER`      : Open the selected item as a webpage
  `1`-`5`             : Toggle post order
  `r` or `F5`         : Refresh page content
  `u`                 : Log in or switch accounts
  `?`                 : Show the help screen
  `q/Q`               : Quit/Force quit

[Authenticated Commands]
  `a/z`               : Upvote/downvote
  `c`                 : Compose a new post or comment
  `e`                 : Edit an existing post or comment
  `d`                 : Delete an existing post or comment
  `i`                 : Display new messages prompt
  `s`                 : Open/close subscribed subreddits list

[Subreddit Mode]
  `l` or `RIGHT`      : Enter the selected submission
  `/`                 : Open a prompt to switch subreddits
  `f`                 : Open a prompt to search the current subreddit

[Submission Mode]
  `h` or `LEFT`       : Return to subreddit mode
  `l` or `RIGHT`      : Open the selected comment in a new window
  `SPACE`             : Fold the selected comment, or load additional comments
  `b`                 : Display URLs with urlview
"""

COMMENT_FILE = """
# Please enter a comment. Lines starting with '#' will be ignored,
# and an empty message aborts the comment.
#
# Replying to {author}'s {type}
{content}
"""

COMMENT_EDIT_FILE = """{content}
# Please enter a comment. Lines starting with '#' will be ignored,
# and an empty message aborts the comment.
#
# Editing your comment
"""

SUBMISSION_FILE = """
# Please enter your submission. Lines starting with '#' will be ignored,
# and an empty message aborts the submission.
#
# The first line will be interpreted as the title
# The following lines will be interpreted as the content
#
# Posting to {name}
"""

SUBMISSION_EDIT_FILE = """{content}
# Please enter your submission. Lines starting with '#' will be ignored,
# and an empty message aborts the submission.
#
# Editing {name}
"""

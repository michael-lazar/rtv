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
Reddit Terminal Viewer

https://github.com/michael-lazar/rtv
======================

[Basic Commands]
  j/k or ▲/▼       : Move the cursor up/down
  m/n or PgUp/PgDn : Jump to the previous/next page
  gg/G             : Jump to the top/bottom of the page
  1-5              : Toggle post order
  r or F5          : Refresh page content
  u                : Log in or switch accounts
  ?                : Show the help screen
  q/Q              : Quit/Force quit

[Authenticated Commands]
  a/z              : Upvote/downvote
  c                : Compose a new post or comment
  e                : Edit an existing post or comment
  d                : Delete an existing post or comment
  i                : Display new messages prompt
  s                : View a list of subscribed subreddits
  S                : View a list of subscribed multireddits
  w                : Save a submission

[Subreddit Commands]
  l or ►           : Enter the selected submission
  o or ENTER       : Open the submission link with your web browser
  /                : Open a prompt to switch subreddits
  f                : Open a prompt to search the current subreddit
  p                : Return to the front page

[Submission Commands]
  h or ◄           : Return to the subreddit
  l or ►           : Open the selected comment in a new window
  o or ENTER       : Open the comment permalink with your web browser
  SPACE            : Fold the selected comment, or load additional comments
  b                : Display URLs with urlview

[Navigating]
  The `/` prompt accepts subreddits in the following formats

  - python
  - /r/python
  - /r/python/new                (sort)
  - /r/python/controversial-year (sort and order)
  - /r/python+linux              (multireddit)
  - /r/front                     (front page)
  - /u/me                        (your submissions)
  - /u/saved                     (your saved posts)
  - /u/spez                      (a user's submissions)
  - /u/multi-mod/m/android       (curated multireddit)
  - /domain/python.org           (search by domain)
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

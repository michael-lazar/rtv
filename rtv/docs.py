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

HELP = """\
====================================
Reddit Terminal Viewer

https://github.com/michael-lazar/rtv
====================================

[Commands]
  j     : Move the cursor down
  k     : Move the cursor up
  n     : Move down one page
  m     : Move up one page
  gg    : Jump to the first post
  G     : Jump to the last post
  1     : Sort by hot
  2     : Sort by top
  3     : Sort by rising
  4     : Sort by new
  5     : Sort by controversial
  p     : Return to the front page
  r     : Refresh page
  u     : Login or logout
  /     : Open the subreddit prompt
  f     : Open the search prompt
  ?     : Show the help screen
  q     : Quit
  Q     : Force quit
  a     : Upvote
  z     : Downvote
  c     : Compose a new submission/comment
  e     : Edit a submission/comment
  d     : Delete a submission/comment
  i     : Display new messages
  s     : Show subscribed subreddits
  S     : Show subscribed multireddits
  w     : Save a submission/comment 
  l     : View comments, or open comment in pager
  h     : Return to subreddit
  o     : Open the submission or comment url
  SPACE : Fold or expand the selected comment tree
  b     : Display urls with urlview

[Prompt]
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

BANNER = """
[1]hot [2]top [3]rising [4]new [5]controversial
"""

FOOTER_SUBREDDIT = """
[?]Help [q]Quit [l]Comments [/]Prompt [u]Login [o]Open [c]Post [a/z]Vote
"""

FOOTER_SUBMISSION = """
[?]Help [q]Quit [h]Return [space]Fold/Expand [o]Open [c]Comment [a/z]Vote
"""

FOOTER_SUBSCRIPTION = """
[?]Help [q]Quit [h]Return [l]Select
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

OAUTH_ACCESS_DENIED = """\
        <h1 style="color: red">Access Denied</h1><hr>
        <p><span style="font-weight: bold">Reddit Terminal Viewer</span> was
        denied access and will continue to operate in unauthenticated mode,
        you can close this window.</p>
"""

OAUTH_ERROR = """\
       <h1 style="color: red">Error</h1><hr>
       <p>{error}</p>
"""

OAUTH_INVALID = """\
       <h1>Wait...</h1><hr>
       <p>This page is supposed to be a Reddit OAuth callback.
       You can't just come here hands in your pocket!</p>
"""

OAUTH_SUCCESS = """\
       <h1 style="color: green">Access Granted</h1><hr>
       <p><span style="font-weight: bold">Reddit Terminal Viewer</span>
       will now log in, you can close this window.</p>
"""

TIME_ORDER_MENU = """
Links from:
  [1] Past hour
  [2] Past 24 hours
  [3] Past week
  [4] Past month
  [5] Past year
  [6] All time
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

AGENT = """\
desktop:https://github.com/michael-lazar/rtv:{version}\
(by /u/civilization_phaze_3)\
"""

SUMMARY = """
RTV (Reddit Terminal Viewer) is a terminal interface to view and interact with reddit.
"""

USAGE = """\
rtv [URL] [-s SUBREDDIT]

  $ rtv https://www.reddit.com/r/programming/comments/7h9l31
  $ rtv -s linux
"""

CONTROLS = """
Move the cursor using the arrow keys or vim style movement.
Press `?` to open the help screen.
"""

HELP = """\
====================================
Reddit Terminal Viewer

https://github.com/michael-lazar/rtv
====================================

[Basic Commands]
  j     : Move the cursor down
  k     : Move the cursor up
  l     : View the currently selected item
  h     : Return to the previous view
  m     : Move the cursor up one page
  n     : Move the cursor down one page
  gg    : Jump to the top of the page
  G     : Jump to the bottom of the page
  1-7   : Sort submissions by category
  r     : Refresh the content on the current page
  u     : Login to your reddit account
  q     : Quit
  Q     : Force quit
  y     : Copy submission permalink to clipboard
  Y     : Copy submission link to clipboard
  F2    : Cycle to the previous color theme
  F3    : Cycle to the next color theme
  ?     : Show the help screen
  /     : Open a prompt to select a subreddit

[Authenticated Commands]
  a     : Upvote
  z     : Downvote
  c     : Compose a new submission or comment
  C     : Compose a new private message
  e     : Edit the selected submission or comment
  d     : Delete the selected submission or comment
  i     : View your inbox (see Inbox Mode)
  s     : View your subscribed subreddits (see Subscription Mode)
  S     : View your subscribed multireddits (see Subscription Mode)
  u     : Logout of your reddit account
  w     : Save the selected submission or comment

[Subreddit Mode]
  l     : View the comments for the selected submission (see Submission Mode)
  o     : Open the selected submission link using your web browser
  SPACE : Mark the selected submission as hidden
  p     : Toggle between the currently viewed subreddit and /r/front
  f     : Open a prompt to search the current subreddit for a text string

[Submission Mode]
  h     : Close the submission and return to the previous page
  l     : View the selected comment using the system's pager
  o     : Open a link in the comment using your web browser
  SPACE : Fold or expand the selected comment and its children
  b     : Send the comment text to the system's urlviewer application
  J     : Move the cursor down the the next comment at the same indentation
  K     : Move the cursor up to the parent comment

[Subscription Mode]
  h     : Close your subscriptions and return to the previous page
  l     : Open the selected subreddit or multireddit

[Inbox Mode]
  h     : Close your inbox and return to the previous page
  l     : View the context of the selected comment
  o     : Open the submission of the selected comment
  c     : Reply to the selected comment or message
  w     : Mark the selected comment or message as seen

[Prompt]
  The / key opens a text prompt at the bottom of the screen. You can use this
  to type in the name of the subreddit that you want to open. The following
  text formats are recognized:

  /python                      - Open a subreddit, shorthand
  /r/python                    - Open a subreddit
  /r/python/new                - Open a subreddit, sorted by category
  /r/python/controversial-year - Open a subreddit, sorted by category and time
  /r/python+linux+commandline  - Open multiple subreddits merged together
  /comments/30rwj2             - Open a submission, shorthand
  /r/python/comments/30rwj2    - Open a submission
  /r/front                     - Open your front page
  /u/me                        - View your submissions
  /u/me/saved                  - View your saved content
  /u/me/hidden                 - View your hidden content
  /u/me/upvoted                - View your upvoted content
  /u/me/downvoted              - View your downvoted content
  /u/spez                      - View a user's submissions and comments
  /u/spez/submitted            - View a user's submissions
  /u/spez/comments             - View a user's comments
  /u/multi-mod/m/android       - Open a user's curated multireddit
  /domain/python.org           - Search for links for the given domain
"""

BANNER_SUBREDDIT = """
[1]hot [2]top [3]rising [4]new [5]controversial [6]gilded
"""

BANNER_SUBMISSION = """
[1]hot [2]top [3]rising [4]new [5]controversial
"""

BANNER_SEARCH = """
[1]relevance [2]top [3]comments [4]new
"""

BANNER_INBOX = """
[1]all [2]unread [3]messages [4]comments [5]posts [6]mentions [7]sent
"""

FOOTER_SUBREDDIT = """
[?]Help [q]Quit [l]Comments [/]Prompt [u]Login [o]Open [c]Post [a/z]Vote [r]Refresh
"""

FOOTER_SUBMISSION = """
[?]Help [q]Quit [h]Return [space]Fold/Expand [o]Open [c]Comment [a/z]Vote [r]Refresh
"""

FOOTER_SUBSCRIPTION = """
[?]Help [q]Quit [h]Return [l]Select Subreddit [r]Refresh
"""

FOOTER_INBOX = """
[?]Help [l]View Context [o]Open Submission [c]Reply [w]Mark Read [r]Refresh
"""

TOKEN = "INSTRUCTIONS"

REPLY_FILE = """<!--{token}
Replying to {{author}}'s {{type}}:
{{content}}

Enter your reply below this instruction block,
an empty message will abort the comment.
{token}-->
""".format(token=TOKEN)

COMMENT_EDIT_FILE = """<!--{token}
Editing comment #{{id}}.
The comment is shown below, update it and save the file.
{token}-->

{{content}}
""".format(token=TOKEN)

SUBMISSION_FILE = """<!--{token}
Submitting a selfpost to {{name}}.

Enter your submission below this instruction block:
- The first line will be interpreted as the title
- The following lines will be interpreted as the body
- An empty message will abort the submission
{token}-->
""".format(token=TOKEN)

SUBMISSION_EDIT_FILE = """<!--{token}
Editing submission #{{id}}.
The submission is shown below, update it and save the file.
{token}-->

{{content}}
""".format(token=TOKEN)

MESSAGE_FILE = """<!--{token}
Compose a new private message

Enter your message below this instruction block:
- The first line should contain the recipient's reddit name
- The second line should contain the message subject
- Subsequent lines will be interpreted as the message body
{token}-->
""".format(token=TOKEN)

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

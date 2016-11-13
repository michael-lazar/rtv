========
Controls
========

.. image:: http://i.imgur.com/xDUQ03C.png

--------------
Basic Commands
--------------

:``j``/``k`` or ``▲``/``▼``: Move the cursor up/down
:``m``/``n`` or ``PgUp``/``PgDn``: Jump to the previous/next page
:``gg``/``G``: Jump to the top/bottom of the page
:``1-5``: Toggle post order (*hot*, *top*, *rising*, *new*, *controversial*)
:``r`` or ``F5``: Refresh page content
:``u``: Log in or switch accounts
:``/``: Open a prompt to switch subreddits
:``?``: Show the help screen
:``q``/``Q``: Quit/Force quit

----------------------
Authenticated Commands
----------------------

Some actions require that you be logged in to your reddit account.
You can log in by pressing ``u`` while inside of the program.
Once you are logged in your username will appear in the top-right corner of the screen.

:``a``/``z``: Upvote/downvote
:``c``: Compose a new post or comment
:``e``: Edit an existing post or comment
:``d``: Delete an existing post or comment
:``i``: Display new messages prompt
:``s``: View a list of subscribed subreddits
:``S``: View a list of subscribed multireddits
:``w``: Save a submission


--------------
Subreddit Mode
--------------

In subreddit mode you can browse through the top submissions on either the front page or a specific subreddit.

:``l`` or ``►``: Enter the selected submission
:``o`` or ``ENTER``:  Open the submission link with your web browser
:``f``: Open a prompt to search the current subreddit
:``p``: Toggle between the front page and the last visited subreddit

The ``/`` prompt accepts subreddits in the following formats

* ``python``
* ``/r/python``
* ``/r/python/new``
* ``/r/python/controversial-year``
* ``/r/python+linux`` supports multireddits
* ``/r/front`` will redirect to the front page
* ``/u/me`` will display your submissions
* ``/u/saved`` will display your saved submissions
* ``/u/spez`` will display submissions from any other user
* ``/u/multi-mod/m/android`` will display a multireddit curated by a user
* ``/domain/python.org`` will display submissions to the stated domain

---------------
Submission Mode
---------------

In submission mode you can view the self text for a submission and browse comments.

:``h`` or ``◄``: Return to the subreddit
:``l`` or ``►``: Open the selected comment in a new window
:``o`` or ``ENTER``: Open the comment permalink with your web browser
:``SPACE``: Fold the selected comment, or load additional comments
:``b``: Display URLs with urlview

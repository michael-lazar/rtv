===========================
RTV: Reddit Terminal Viewer
===========================

RTV is an application that allows you to view and interact with reddit from your terminal.
It is compatible with *most* terminal emulators on Linux and OSX.

.. image:: http://i.imgur.com/xpOEi1E.png

RTV is built in **python** using the **curses** library.

---------------

|pypi| |python| |downloads|

---------------

* `Installation`_
* `Usage`_
* `Configuration`_
* `FAQ`_
* `Changelog`_
* `Contributors`_
* `License`_

============
Installation
============

Install using pip

.. code-block:: bash

   $ sudo pip install rtv

Or clone the repository

.. code-block:: bash

   $ git clone https://github.com/michael-lazar/rtv.git
   $ cd rtv
   $ sudo python3 setup.py install

The installation will place a script in the system path

.. code-block:: bash

   $ rtv
   $ rtv --help

See the `FAQ`_ for more information on common installation problems

=====
Usage
=====

RTV supports browsing both subreddits and submission comments.

Navigating is simple and intuitive.
Move the cursor using either the arrow keys or *Vim* style movement.
Move **up** and **down** to scroll through the page.
Move **right** to view the selected submission, and **left** to exit the submission.

--------------
Basic Commands
--------------

:``j``/``k`` or ``▲``/``▼``: Move the cursor up/down
:``m``/``n`` or ``PgUp``/``PgDn``: Jump to the previous/next page
:``1-5``: Toggle post order (*hot*, *top*, *rising*, *new*, *controversial*)
:``r`` or ``F5``: Refresh page content
:``u``: Log in or switch accounts
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

--------------
Subreddit Mode
--------------

In subreddit mode you can browse through the top submissions on either the front page or a specific subreddit.

:``l`` or ``►``: Enter the selected submission
:``o`` or ``ENTER``:  Open the submission link with your web browser
:``/``: Open a prompt to switch subreddits
:``f``: Open a prompt to search the current subreddit

The ``/`` prompt accepts subreddits in the following formats

* ``/r/python``
* ``/r/python/new``
* ``/r/python+linux`` supports multireddits
* ``/r/front`` will redirect to the front page
* ``/r/me`` will display your submissions

---------------
Submission Mode
---------------

In submission mode you can view the self text for a submission and browse comments.

:``h`` or ``◄``: Return to the subreddit
:``o`` or ``ENTER``: Open the comment permalink with your web browser
:``SPACE``: Fold the selected comment, or load additional comments

=============
Configuration
=============

------
Editor
------

RTV allows users to compose comments and replies using their preferred text editor (**vi**, **nano**, **gedit**, etc).
You can specify which text editor you would like to use by setting the ``$RTV_EDITOR`` environment variable.

.. code-block:: bash

   $ export RTV_EDITOR=gedit

If no editor is specified, RTV will fallback to the system's default ``$EDITOR``, and finally to ``nano``.

-----------
Web Browser
-----------

RTV has the capability to open links inside of your web browser.
By default RTV will use the system's browser.
On most systems this corresponds to a graphical browser such as Firefox or Chrome.
If you prefer to stay in the terminal, use ``$BROWSER`` to specify a console-based web browser.
`w3m <http://w3m.sourceforge.net/>`_, `lynx <http://lynx.isc.org/>`_, and `elinks <http://elinks.or.cz/>`_ are all good choices.

.. code-block:: bash

   $ export BROWSER=w3m

--------------
Authentication
--------------

RTV uses OAuth to facilitate logging into your reddit user account [#]_. The login process follows these steps:

1. You initiate a login by pressing the ``u`` key.
2. You're redirected to a webbrowser where reddit will ask you to login and authorize RTV.
3. RTV uses the generated token to login on your behalf.
4. The token is stored on your computer at ``~/.config/rtv/refresh-token`` for future sessions.   You can disable this behavior by setting ``persistent=False`` in your RTV config.

Note that RTV no longer allows you to input your username/password directly. This method of cookie based authentication has been deprecated by reddit and will not be supported in future releases [#]_.

.. [#] `<https://github.com/reddit/reddit/wiki/OAuth2>`_
.. [#] `<https://www.reddit.com/r/redditdev/comments/2ujhkr/important_api_licensing_terms_clarified/>`_

-----------
Config File
-----------

RTV will read a configuration placed at ``~/.config/rtv/rtv.cfg`` (or ``$XDG_CONFIG_HOME``).
Each line in the file will replace the corresponding default argument in the launch script.
This can be used to avoid having to re-enter login credentials every time the program is launched.

Example initial config:

**rtv.cfg**

.. code-block:: ini

  [rtv]
  # Log file location
  log=/tmp/rtv.log

  # Default subreddit
  subreddit=CollegeBasketball

  # Default submission link - will be opened every time the program starts
  # link=http://www.reddit.com/r/CollegeBasketball/comments/31irjq

  # Turn on ascii-only mode and disable all unicode characters
  # This may be necessary for compatibility with some terminal browsers
  # ascii=True

  # Enable persistent storage of your authentication token
  # This allows you to remain logged in when you restart the program
  persistent=True


===
FAQ
===

Why am I getting an error during installation/when launching rtv?
  If your distro ships with an older version of python 2.7 or python-requests,
  you may experience SSL errors or other package incompatibilities. The
  easiest way to fix this is to install rtv using python 3. If you
  don't already have pip3, see http://stackoverflow.com/a/6587528 for setup
  instructions. Then do

  .. code-block:: bash

    $ sudo pip uninstall rtv
    $ sudo pip3 install -U rtv

How do I run the repository code directly?
  This project is structured to be run as a python *module*. This means that in
  order to resolve imports you need to launch using python's ``-m`` flag.
  This method works for all versions of python. See the example below, which
  assumes that you have cloned the repository into the directory
  **~/rtv_project**.

  .. code-block:: bash

    $ cd ~/rtv_project
    $ python3 -m pip install -r requirements.py3.txt
    $ python3 -m rtv

=========
Changelog
=========
Please see `CHANGELOG.rst <https://github.com/michael-lazar/rtv/blob/master/CHANGELOG.rst>`_.


============
Contributors
============
Please see `CONTRIBUTORS.rst <https://github.com/michael-lazar/rtv/blob/master/CONTRIBUTORS.rst>`_.


=======
License
=======
Please see `LICENSE <https://github.com/michael-lazar/rtv/blob/master/LICENSE>`_.


.. |python| image:: https://img.shields.io/badge/python-2.7%2C%203.5-blue.svg?style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Supported Python versions

.. |pypi| image:: https://img.shields.io/pypi/v/rtv.svg?label=version&style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version

.. |downloads| image:: https://img.shields.io/pypi/dm/rtv.svg?period=month&style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Downloads
===========================
RTV: Reddit Terminal Viewer
===========================

RTV is an application that allows you to view and interact with reddit from your terminal. It is compatible with *most* terminal emulators on Linux and OSX.

.. image:: http://i.imgur.com/W1hxqCt.png

RTV is built in **python** using the **curses** library.

---------------

|pypi| |python| |downloads|

---------------

* `Installation`_
* `Usage`_
* `Configuration`_
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
   $ sudo python setup.py install

The installation will place a script in the system path

.. code-block:: bash

   $ rtv
   $ rtv --help

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
:``o`` or ``ENTER``: Open the selected item as a webpage
:``r`` or ``F5``: Refresh page content
:``u``: Log in or switch accounts
:``?``: Show the help screen
:``q``: Quit

----------------------
Authenticated Commands
----------------------

Some actions require that you be logged in to your reddit account. To log in you can either:

1. provide your username as a command line argument ``-u`` (your password will be securely prompted), or
2. press ``u`` while inside of the program

Once you are logged in your username will appear in the top-right corner of the screen.

:``a``/``z``: Upvote/downvote
:``c``: Compose a new post or comment
:``e``: Edit an existing post or comment
:``d``: Delete an existing post or comment

--------------
Subreddit Mode
--------------

In subreddit mode you can browse through the top submissions on either the front page or a specific subreddit.

:``l`` or ``►``: Enter the selected submission
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

-----------
Config File
-----------

RTV will read a configuration placed at ``~/.config/rtv/rtv.cfg`` (or ``$XDG_CONFIG_HOME``).
Each line in the file will replace the corresponding default argument in the launch script.
This can be used to avoid having to re-enter login credentials every time the program is launched.

Example config:

.. code-block:: ini

  [rtv]
  username=MyUsername
  password=MySecretPassword

  # Log file location
  log=/tmp/rtv.log

  # Default subreddit
  subreddit=CollegeBasketball

  # Default submission link - will be opened every time the program starts
  # link=http://www.reddit.com/r/CollegeBasketball/comments/31irjq

  # Turn on ascii-only mode and disable all unicode characters
  # This may be necessary for compatibility with some terminal browsers
  # ascii=True


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


.. |python| image:: https://img.shields.io/badge/python-2.7%2C%203.4-blue.svg?style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Supported Python versions

.. |pypi| image:: https://img.shields.io/pypi/v/rtv.svg?label=version&style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version

.. |downloads| image:: https://img.shields.io/pypi/dm/rtv.svg?period=month&style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Downloads

.. image:: https://pypip.in/version/rtv/badge.svg?text=version&style=flat
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version

.. image:: https://pypip.in/py_versions/rtv/badge.svg?style=flat
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Supported Python versions

======================
Reddit Terminal Viewer
======================

Browse Reddit from your terminal

.. image:: http://i.imgur.com/W1hxqCt.png

RTV is built in **python** using the **curses** library, and is compatible with *most* terminal emulators on Linux and OS X.

-------------
Update (v1.1)
-------------

Users can now post comments!

.. image:: http://i.imgur.com/twls7iM.png

------------
Installation
------------

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

-----
Usage 
-----

RTV currently supports browsing both subreddits and individual submissions. In each mode the controls are slightly different.

**Global Commands**

:``▲``/``▼`` or ``j``/``k``: Scroll to the prev/next item
:``a``/``z``: Upvote/downvote the selected item
:``o``: Open the selected item in the default web browser
:``r``: Refresh the current page
:``?``: Show the help message
:``q``: Quit

**Subreddit Mode**

In subreddit mode you can browse through the top submissions on either the front page or a specific subreddit.

:``►`` or ``l``: View comments for the selected submission
:``/``: Open a prompt to switch subreddits

The ``/`` prompt accepts subreddits in the following formats

* ``/r/python``
* ``/r/python/new``
* ``/r/python+linux`` supports multireddits
* ``/r/front`` will redirect to the front page

**Submission Mode**

In submission mode you can view the self text for a submission and browse comments.

:``◄`` or ``h``: Return to subreddit mode
:``►`` or ``l``: Fold the selected comment, or load additional comments
:``c``: Comment/reply on the selected item

-------------
Configuration
-------------

RTV will read a configuration file located at **~/.rtv**.
This can be used to avoid having to re-enter login credentials every time the program is launched.
Each line in the file will replace the corresponding default argument in the launch script.

Example config:

**~/.rtv**
::

  [rtv]
  username=MyUsername
  password=MySecretPassword
  
  # Default subreddit
  subreddit=CollegeBasketball

RTV allows users to compose comments and replys using their preferred text editor (**vi**, **nano**, **gedit**, etc).
Set the environment variable ``RTV_EDITOR`` to specify which editor the program should use.

.. code-block:: bash

   $ export RTV_EDITOR=gedit

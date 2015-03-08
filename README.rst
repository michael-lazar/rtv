.. image:: https://pypip.in/version/rtv/badge.svg?text=version&style=flat
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version

======================
Reddit Terminal Viewer
======================

Browse Reddit from your terminal

RTV is built in python using the curses library, and is compatable with *most* terminal emulators on Linux and OS X.

.. image:: http://i.imgur.com/4a3Yrov.gif

------------
Installation
------------

Install using pip

.. code-block:: bash
   
   $ sudo pip install --pre rtv

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
:``o``: Open the selected item in the default web browser
:``r`` or ``F5``: Refresh the current page
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


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
* `Configuration`_
* `Usage`_
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


=============
Configuration
=============

RTV will read a configuration file located at ``$XDG_CONFIG_HOME/rtv/rtv.cfg`` or ``~/.config/rtv/rtv.cfg`` if ``$XDG_CONFIG_HOME`` is not set.
This can be used to avoid having to re-enter login credentials every time the program is launched.
Each line in the file will replace the corresponding default argument in the launch script.

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

  # Enable unicode characters (experimental)
  # This is known to be unstable with east asian wide character sets
  # unicode=true

RTV allows users to compose comments and replys using their preferred text editor (**vi**, **nano**, **gedit**, etc).
Set the environment variable ``RTV_EDITOR`` to specify which editor the program should use.

.. code-block:: bash

   $ export RTV_EDITOR=gedit


=====
Usage 
=====

RTV currently supports browsing both subreddits and individual submissions. In each mode the controls are slightly different.

---------------
Global Commands
---------------

:``▲``/``▼`` or ``j``/``k``: Scroll to the prev/next item
:``a``/``z``: Upvote/downvote the selected item
:``ENTER`` or ``o``: Open the selected item in the default web browser
:``r``: Refresh the current page
:``u``: Login and logout of your user account
:``?``: Show the help screen
:``q``: Quit

--------------
Subreddit Mode
--------------

In subreddit mode you can browse through the top submissions on either the front page or a specific subreddit.

:``►`` or ``l``: View comments for the selected submission
:``/``: Open a prompt to switch subreddits
:``f``: Open a prompt to search the current subreddit
:``p``: Post a new submission to the current subreddit
:``e``: Edit the selected submission
:``d``: Delete the selected submission


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

:``◄`` or ``h``: Return to subreddit mode
:``►`` or ``l``: Fold the selected comment, or load additional comments
:``c``: Post a new comment on the selected item
:``e``: Edit the selected comment
:``d``: Delete the selected comment

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


.. |python| image:: https://pypip.in/py_versions/rtv/badge.svg?style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Supported Python versions

.. |pypi| image:: https://pypip.in/version/rtv/badge.svg?text=version&style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version
    
.. |downloads| image:: https://pypip.in/download/rtv/badge.svg?period=month&style=flat-square
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Downloads

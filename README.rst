======================
Reddit Terminal Viewer
======================

.. image:: https://pypip.in/version/rtv/badge.svg?text=version
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version

**Reddit Terminal Viewer (RTV)** is a lightweight browser for Reddit (www.reddit.com) built into a terminal window.
RTV is built in Python and utilizes the **curses** library. 
It is compatible with a large range of terminal emulators on Linux and OSX systems. 

.. image:: http://i.imgur.com/4a3Yrov.gif

------------
Installation
------------
The recommended installation method is pip.

.. code-block:: bash
   
   $ sudo pip install --pre rtv

Alternatively, clone the repo and install with python.

.. code-block:: bash

   $ git clone https://github.com/michael-lazar/rtv.git
   $ cd rtv
   $ sudo python setup.py install

As part of the installation, an executable script will be placed in your system path.

.. code-block:: bash

   $ rtv
   $ rtv --help

-----
Usage 
-----

RTV currently supports browsing both subreddits and individual submissions. In each mode the controls are slightly different.

**Global Commands**

:``Arrow Keys`` or ``hjkl``: RTV supports both the arrow keys and vim bindings for navigation. Move up and down to scroll through items on the page.
:``r`` or ``F5``: Refresh the current page.
:``q``: Quit the program.
:``o``: Open the url of the selected item in the default web browser.

**Subreddit Mode**

In subreddit mode you can browse through the top submissions on either the front page or a specific subreddit.

:``Right`` or ``Enter``: Open the currently selected submission in a new page.
:``/``: Open a prompt to switch to a different subreddit. For example, pressing ``/`` and typing *python* will open */r/python*. You can return to Reddit's front page by using the alias */r/front*.

**Submission Mode**

In submission mode you can view the self text for a submission and browse comments.

:``Right`` or ``Enter``: Toggle the currently selected comment between hidden and visible. Alternatively, load additional comments identified by *[+] more comments*.
:``Left``: Exit the submission page and return to the subreddit.

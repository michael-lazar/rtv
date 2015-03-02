======================
Reddit Terminal Viewer
======================
**Reddit Terminal Viewer (RTV)** is a lightweight browser for Reddit (www.reddit.com) built into a terminal window.
RTV is built in Python and utilizes the **curses** library. 
It is compatible with a large range of terminal emulators on Linux and OSX systems. 

.. image:: /resources/demo.gif

------------
Installation
------------
Reddit Terminal Viewer is Py2/Py3 compatible and can be installed via python setuptools.
 
.. code-block:: bash

   $ git clone https://github.com/michael-lazar/rtv.git
   $ cd rtv
   $ sudo python setup.py install

After the installation has finished, a script will be placed in the system path. The program can then be started by typing

.. code-block:: bash

   $ rtv

Additional options can be viewed with

.. code-block:: bash

   $ rtv --help

--------
Controls 
--------

Navigating content in RTV is primarily done via the arrow keys.

:``Up/Down``: Control the cursor and scroll through items.
:``r`` or ``F5``: Refresh the page
:``q``: Quit

RTV currently supports browsing both subreddits and individual submissions. In each mode, controls are slightly different.

**Subreddit Mode**

:``Right`` or ``Enter``: Open the page for the currently selected submission
:``/``: Open a prompt to switch to a different subreddit

**Submission Mode**

:``Left``: Exit the submission and return to the subreddit
:``Right`` or ``Enter``: Toggle the selected comment and its children between hidden and visible states

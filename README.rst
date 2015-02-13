======================
Reddit Terminal Viewer
======================
**Reddit Terminal Viewer (RTV)** is a python application that enables browsing content from Reddit (www.reddit.com) on a terminal window.
RTV utilizes the **curses** library and is compatible with a large range of terminals.

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

**Subreddit Mode**

:``Up/Down``: move cursor
:``Right`` or ``Enter``: view the selected submission
:``q``: quit
:``r`` or ``F5``: refresh
:``/``: open prompt to nagivate to a different subreddit

**Submission Mode**

:``Up/Down``: move cursor
:``Left``: return to subreddit
:``Right`` or ``Enter``: Toggle the selected comment and its children between hidden and visible
:``q``: quit
:``r`` or ``F5``: refresh

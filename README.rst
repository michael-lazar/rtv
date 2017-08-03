============================
RTV (Reddit Terminal Viewer)
============================

| RTV provides an interface to view and interact with reddit from your terminal.
| It's compatible with *most* terminal emulators on Linux and OS X.

.. image:: http://i.imgur.com/9utJir2.png

|
| RTV is built in **python** using the **curses** library.

---------------

|pypi| |python| |travis-ci| |coveralls| |gitter|

---------------

* `Demo`_
* `Installation`_
* `Usage`_
* `Settings`_
* `FAQ`_
* `Contributing`_
* `License`_

====
Demo
====

.. image:: http://i.imgur.com/aNZWxnW.gif

============
Installation
============

--------------
Python package
--------------

RTV is available on `PyPI <https://pypi.python.org/pypi/rtv/>`_ and can be installed with pip:

.. code-block:: bash

    $ pip install rtv

---------------
Native packages
---------------

**macOS**

.. code-block:: bash

    $ brew install rtv

**Arch Linux**

.. code:: bash

    $ # Install the latest official release
    $ yaourt -S rtv
    $ # Or to keep up to date with the master branch
    $ yaourt -S rtv-git

=====
Usage
=====

To run the program, type 

.. code-block:: bash

    $ rtv --help

--------
Controls
--------

Move the cursor using either the arrow keys or *Vim* style movement

- Press ``up`` and ``down`` to scroll through submissions
- Press ``right`` to view the selected submission and ``left`` to return
- Press ``space`` to expand/collapse comments
- Press ``u`` to login
- Press ``?`` to open the help screen

Press ``/`` to open the navigation prompt, where you can type things like

- ``/front``
- ``/r/commandprompt+linuxmasterrace``
- ``/r/programming/controversial-week``
- ``/u/me``
- ``/u/multi-mod/m/art``
- ``/domain/github.com``

See `CONTROLS <https://github.com/michael-lazar/rtv/blob/master/CONTROLS.rst>`_ for the full list of commands

========
Settings
========

------------------
Configuration File
------------------

Configuration files are stored in the ``{HOME}/.config/rtv/`` directory

See `rtv.cfg <https://github.com/michael-lazar/rtv/blob/master/rtv/templates/rtv.cfg>`_ for the full list of configurable options. You can clone this file into your home directory by running

.. code-block:: bash

    $ rtv --copy-config
    
-------------------
Viewing Media Links
-------------------

You can use `mailcap <https://en.wikipedia.org/wiki/Media_type#Mailcap>`_ to configure
how RTV will open different types of links

.. image:: http://i.imgur.com/ueQ3w0P.gif

|
| A mailcap file allows you to associate different MIME media types, like ``image/jpeg`` or ``video/mp4``, with shell commands.

This feature is disabled by default because it takes a a few extra steps to configure. To get started, copy the default mailcap template to your home directory.

.. code-block:: bash

    $ rtv --copy-mailcap

This template contains examples for common MIME types that work with popular reddit websites like *imgur*, *youtube*, and *gfycat*. Open the mailcap template and follow the `instructions <https://github.com/michael-lazar/rtv/blob/master/rtv/templates/mailcap>`_ listed inside. 

Once you've setup your mailcap file, enable it by launching rtv with the ``rtv --enable-media`` flag (or set it in your **rtv.cfg**)

---------------------
Environment Variables
---------------------

The default programs that RTV interacts with can be configured through environment variables

``$RTV_EDITOR``
  | A program used to compose text submissions and comments, e.g. **vim**, **emacs**, **gedit**
  | *If not specified, will fallback to ``$VISUAL`` and ``$EDITOR`` in that order.*

``$RTV_BROWSER``
  | A program used to open links to external websites, e.g. **firefox**, **google-chrome**, **w3m**, **lynx**, **elinks**
  | *If not specified, will fallback to ``$BROWSER``, or try to intelligently choose a browser supported by your system.*

``$RTV_URLVIEWER``
  | A tool used to extract hyperlinks from blocks of text, e.g.  `urlview <https://github.com/sigpipe/urlview>`_, `urlscan <https://github.com/firecat53/urlscan>`_
  | *If not specified, will fallback to urlview if it is installed.*

------------------------
Copying to the Clipboard
------------------------
RTV supports copying submission links to the OS clipboard.
On macOS this is supported out of the box.
On Linux systems you will need to install either `xsel <http://www.vergenet.net/~conrad/software/xsel/>`_ or `xclip <https://sourceforge.net/projects/xclip/>`_.

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

Why do I see garbled text like ``M-b~@M-"`` or ``^@``?
  Quick fix
    Try starting RTV in ascii-only mode with ``rtv --ascii``
  
  Explanation
    This type of text usually shows up when python is unable to render
    unicode properly.
    
    1. Make sure that the terminal/font that you're using supports unicode
    2. Try `setting the LOCALE to utf-8 <https://perlgeek.de/en/article/set-up-a-clean-utf8-environment>`_
    3. Your python may have been built against the wrong curses library,
       see `here <stackoverflow.com/questions/19373027>`_ and
       `here <https://bugs.python.org/issue4787>`_ for more information
  
How do I run the code directly from the repository?
  This project is structured to be run as a python *module*. This means that in
  order to resolve imports you need to launch using python's ``-m`` flag.
  This method works for all versions of python. See the example below, which
  assumes that you have cloned the repository into the directory
  **~/rtv_project**.

  .. code-block:: bash

    $ cd ~/rtv_project
    $ python3 -m rtv
  
============
Contributing
============
All feedback and suggestions are welcome, just post an issue!

Before writing any code, please read the `Contributor Guidelines <https://github.com/michael-lazar/rtv/blob/master/CONTRIBUTING.rst>`_.

=======
License
=======
This project is distributed under the `MIT <https://github.com/michael-lazar/rtv/blob/master/LICENSE>`_ license.


.. figure:: http://i.imgur.com/quDzox3.png
   :target: https://github.com/Swordfish90/cool-retro-term
   

.. |python| image:: https://img.shields.io/badge/python-2.7%2C%203.6-blue.svg
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Supported Python versions

.. |pypi| image:: https://img.shields.io/pypi/v/rtv.svg?label=version
    :target: https://pypi.python.org/pypi/rtv/
    :alt: Latest Version
    
.. |travis-ci| image:: https://travis-ci.org/michael-lazar/rtv.svg?branch=master
    :target: https://travis-ci.org/michael-lazar/rtv
    :alt: Build

.. |coveralls| image:: https://coveralls.io/repos/michael-lazar/rtv/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/michael-lazar/rtv?branch=master
    :alt: Coverage
    
.. |gitter| image:: https://img.shields.io/gitter/room/michael-lazar/rtv.js.svg
    :target: https://gitter.im/michael-lazar/rtv
    :alt: Chat

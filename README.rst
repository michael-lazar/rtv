============================
RTV (Reddit Terminal Viewer)
============================

| RTV provides an interface to view and interact with reddit from your terminal.
| It's compatible with *most* terminal emulators on Linux and OS X.

.. image:: http://i.imgur.com/Ek13lqM.png

|
| RTV is built in **python** using the **curses** library.

---------------

|pypi| |python| |travis-ci| |coveralls| |gitter|

Note to users - a security `vulnerability <https://github.com/michael-lazar/rtv/issues/295>`_ has been discovered in rtv versions prior to v1.12.1. A patch has been applied and it is strongly advised that you upgrade to the latest version.

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

.. figure:: http://i.imgur.com/UeKbK8z.png
   :target: https://asciinema.org/a/81251?speed=2

============
Installation
============

Install using pip (**recommended**)

.. code-block:: bash

    $ pip install rtv

or clone the repository

.. code-block:: bash

    $ git clone https://github.com/michael-lazar/rtv.git
    $ cd rtv
    $ python3 setup.py install

on Arch Linux or Arch based distros (Antergos, Manjaro, `etc.`_) you can install directly with an `aur helper`_ such as yaourt.

**WARNING - The Aur package is temporarily broken, see** `here`_ **for a workaround**

.. code:: bash

    $ yaourt -S rtv
    $ # or to keep up to date with the master branch
    $ yaourt -S rtv-git

.. _here: https://aur.archlinux.org/packages/rtv/
.. _etc.: https://wiki.archlinux.org/index.php/Arch_based_distributions_(active)
.. _aur helper: https://wiki.archlinux.org/index.php/AUR_helpers#AUR_search.2Fbuild_helpers

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

-------------
Configuration
-------------

Configuration files are stored in the ``{HOME}/.config/rtv/`` directory

See `rtv.cfg <https://github.com/michael-lazar/rtv/blob/master/rtv/templates/rtv.cfg>`_ for the full list of configurable options. You can clone this file into your home directory by running

.. code-block:: bash

    $ rtv --copy-config
    
-----
Media
-----

You can use `mailcap <https://en.wikipedia.org/wiki/Media_type#Mailcap>`_ to configure
how RTV will open different types of links

.. image:: http://i.imgur.com/ueQ3w0P.gif

|
| A mailcap file allows you to associate different MIME media types, like ``image/jpeg`` or ``video/mp4``, with shell commands.

This feature is disabled by default because it takes a a few extra steps to configure. To get started, copy the default mailcap template to your home directory.

.. code-block:: bash

    $ rtv --copy-mailcap

This template contains examples for common MIME types as well as popular reddit websites like `imgur <http://imgur.com/>`_, `youtube <https://www.youtube.com/>`_, and `gfycat <https://gfycat.com/>`_. Open the mailcap template and follow the `instructions <https://github.com/michael-lazar/rtv/blob/master/rtv/templates/mailcap>`_ listed inside. 

Once you've setup your mailcap file, enable it by launching rtv with the ``rtv --enable-media`` flag (or set it in your **rtv.cfg**)

-----------
Environment
-----------

RTV will respect the following environment variables when accessing external programs

``$BROWSER``
  | Submission links will be opened inside of your web browser.
  | On most systems the default web browser will open in a new window. If you prefer the complete terminal experience, try using a console-based web browser (`w3m <http://w3m.sourceforge.net/>`_, `lynx <http://lynx.isc.org/>`_, and `elinks <http://elinks.or.cz/>`_ are all good choices).
``$PAGER``
  | Extra long comments and submissions wil be viewed through the system pager.
``$RTV_EDITOR``
 | Compose posts and replying to comments is done using your preferred text editor.
 | If not specified, the default system ``$EDITOR`` (or `nano <https://www.nano-editor.org/>`_) will be used.
``$RTV_URLVIEWER``
 | A url viewer can be used to extract links from inside of comments.
 | `urlview <https://github.com/sigpipe/urlview>`_ and `urlscan <https://github.com/firecat53/urlscan>`_ are known to be compatible. These applications don't come pre-installed, but are available through most systems' package managers.

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


.. |python| image:: https://img.shields.io/badge/python-2.7%2C%203.5-blue.svg
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


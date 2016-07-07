============================
RTV (Reddit Terminal Viewer)
============================

| RTV provides an interface to view and interact with reddit from your terminal.
| It's compatible with *most* terminal emulators on Linux and OSX.

.. image:: http://i.imgur.com/Ek13lqM.png

`DEMO <https://asciinema.org/a/31609?speed=2&autoplay=1>`_

RTV is built in **python** using the **curses** library.

---------------

|pypi| |python| |travis-ci| |coveralls| |gitter|

---------------

* `Installation`_
* `Usage`_
* `Settings`_
* `FAQ`_
* `Changelog`_
* `License`_

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

on Arch Linux or Arch based distros (Antergos, Manjaro, `etc.`_) you can install directly using an `aur helper`_ such as yaourt. There's also an *rtv-git* package if you wish to keep up to date with the latest development code.

.. code:: bash

    $ yaourt -S rtv

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

- Press **up** and **down** to scroll through submissions.
- Press **right** to view the selected submission and **left** to return.
- Press **?** to open the help screen.

See `CONTROLS <https://github.com/michael-lazar/rtv/blob/master/CONTROLS.rst>`_ for the complete list of available commands.

--------------
Authentication
--------------

RTV enables you to login to your reddit account in order to perform actions like voting and leaving comments.
The login process uses OAuth [#]_ and follows these steps:

1. Initiate the login by pressing the ``u`` key.
2. Open a new webpage where reddit will ask you to authorize the application.
3. Click **Accept**.

RTV will retrieve an auth token with your information and store it locally in ``{HOME}/.config/rtv/refresh-token``.
You can disable storing the token by setting ``persistent=False`` in the config.

Note that RTV no longer allows you to input your username/password directly. This method of cookie based authentication has been deprecated by reddit [#]_.

.. [#] `<https://github.com/reddit/reddit/wiki/OAuth2>`_
.. [#] `<https://www.reddit.com/r/redditdev/comments/2ujhkr/important_api_licensing_terms_clarified/>`_

========
Settings
========

-------------
Configuration
-------------

Configuration settings are stored in ``{HOME}/.config/rtv/rtv.cfg``.
Auto-generate the config file by running

.. code-block:: bash

    $ rtv --copy-config

See the `default config <https://github.com/michael-lazar/rtv/blob/master/rtv/rtv.cfg>`_ for the full list of settings.

------
Editor
------

You can compose posts and reply to comments using your preferred text editor.
Set the editor by changing ``$RTV_EDITOR`` in your environment.

.. code-block:: bash

    $ export RTV_EDITOR=gedit

If not specified, the default system ``$EDITOR`` (or *nano*) will be used.

-----------
Web Browser
-----------

You can open submission links using your web browser.
On most systems the default web browser will open in a new window.
If you prefer the complete terminal experience, set ``$BROWSER`` to a console-based web browser.

.. code-block:: bash

    $ export BROWSER=w3m

`w3m <http://w3m.sourceforge.net/>`_, `lynx <http://lynx.isc.org/>`_, and `elinks <http://elinks.or.cz/>`_ are all good choices.

----------
Url Viewer
----------

You can open links displayed inside of comments by taking advantage of a url extraction program.
Use ``$RTV_URLVIEWER`` to specify a custom url viewer.

.. code-block:: bash

    $ export RTV_URLVIEWER=urlview

`urlview <https://github.com/sigpipe/urlview>`_ and `urlscan <https://github.com/firecat53/urlscan>`_ are known to be compatible, but any program that accepts text via a stdin pipe will do.
These applications do not come pre-installed on most systems.

**Ubuntu**

.. code-block:: bash

    $ sudo apt-get install urlview

**Mac with Homebrew**

.. code-block:: bash

    $ brew install urlview


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

How do I run the tests?
  This project uses `pytest <http://pytest.org/>`_ and `VCR.py <https://vcrpy.readthedocs.org/>`_.

  .. code-block:: bash
    
    $ pip3 install pytest
    $ # The pip release for VCR.py is out-of-date
    $ pip3 install git+https://github.com/kevin1024/vcrpy.git
    $ cd ~/rtv_project
    $ # Run the full suite
    $ PYTHONPATH=. py.test
    $ # or a single test
    $ PYTHONPATH=. py.test tests/test_config.py::test_copy_default_config

  VCR.py will record HTTP requests made during the test run and store
  them in *tests/cassettes/*. By default these cassettes are read-only,
  if you would like to record new cassettes you must provide your own refresh token.

  .. code-block:: bash

     $ PYTHONPATH=. py.test --record-mode=once --refresh-token=~/.config/rtv/refresh-token
  
=========
Changelog
=========
Please see `CHANGELOG <https://github.com/michael-lazar/rtv/blob/master/CHANGELOG.rst>`_

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


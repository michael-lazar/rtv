# RTV (Reddit Terminal Viewer)

RTV provides an interface to view and interact with reddit from your terminal.<br/>
It's compatible with *most* terminal emulators on Linux and OS X.

<p align="center">
<img alt="title image" src="resources/title_image.png"/>
</p>

RTV is built in **python** using the **curses** library.

---

<p align="center">
  <a href="https://pypi.python.org/pypi/rtv/">
    <img alt="pypi" src="https://img.shields.io/pypi/v/rtv.svg?label=version"/>
  </a>
  <a href="https://pypi.python.org/pypi/rtv/">
    <img alt="python" src="https://img.shields.io/badge/python-2.7%2C%203.6-blue.svg"/>
  </a>
  <a href="https://travis-ci.org/michael-lazar/rtv">
    <img alt="travis-ci" src="https://travis-ci.org/michael-lazar/rtv.svg?branch=master"/>
  </a>
  <a href="https://coveralls.io/github/michael-lazar/rtv?branch=master">
    <img alt="coveralls" src="https://coveralls.io/repos/michael-lazar/rtv/badge.svg?branch=master&service=github"/>
  </a>
  <a href="https://gitter.im/michael-lazar/rtv">
    <img alt="gitter" src="https://img.shields.io/gitter/room/michael-lazar/rtv.js.svg"/>
  </a>
</p>

---

* [Demo](#demo)  
* [Installation](#installation)  
* [Usage](#usage)  
* [Settings](#settings)  
* [FAQ](#faq)  
* [Contributing](#contributing)  
* [License](#license)  

## Demo

<p align="center">
<img alt="title image" src="resources/demo.gif"/>
</p>

## Installation

### Python package

RTV is available on [PyPI](https://pypi.python.org/pypi/rtv/) and can be installed with pip:

```bash
$ pip install rtv
```

### Native packages

Check [Repology](https://repology.org/metapackage/rtv/information) for an up-to-date list of supported packages:

**macOS**

```bash
$ brew install rtv
```

**Debian 9+, Ubuntu 17.04+**

```bash
$ apt install rtv
```

**Fedora 24+**

```bash
$ yum install rtv
```

**Arch Linux**

```bash
$ # Install the latest official release
$ yaourt -S rtv
$ # Or to keep up to date with the master branch
$ yaourt -S rtv-git
```

## Usage

To run the program, type 

```bash
$ rtv --help
```

### Controls

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

See [CONTROLS](https://github.com/michael-lazar/rtv/blob/master/CONTROLS.rst) for the full list of commands

## Settings

### Configuration File

Configuration files are stored in the ``{HOME}/.config/rtv/`` directory

See [rtv.cfg](https://github.com/michael-lazar/rtv/blob/master/rtv/templates/rtv.cfg) for the full list of configurable options. You can clone this file into your home directory by running

```bash
$ rtv --copy-config
```

### Viewing Media Links

You can use [mailcap](https://en.wikipedia.org/wiki/Media_type#Mailcap) to configure how RTV will open different types of links

<p align="center">
<img alt="title image" src="resources/mailcap.gif"/>
</p>

A mailcap file allows you to associate different MIME media types, like ``image/jpeg`` or ``video/mp4``, with shell commands. This feature is disabled by default because it takes a a few extra steps to configure. To get started, copy the default mailcap template to your home directory.

```bash
$ rtv --copy-mailcap
```

This template contains examples for common MIME types that work with popular reddit websites like *imgur*, *youtube*, and *gfycat*. Open the mailcap template and follow the [instructions](https://github.com/michael-lazar/rtv/blob/master/rtv/templates/mailcap) listed inside. 

Once you've setup your mailcap file, enable it by launching rtv with the ``rtv --enable-media`` flag (or set it in your **rtv.cfg**)

### Environment Variables

The default programs that RTV interacts with can be configured through environment variables

<dl>
  <dt>$RTV_EDITOR</dt>
  <dd>A program used to compose text submissions and comments, e.g. <strong>vim</strong>, <strong>emacs</strong>, <strong>gedit</strong>
  <br/> <em>If not specified, will fallback to $VISUAL and $EDITOR in that order.</em></dd>
  
  <dt>$RTV_BROWSER</dt>
  <dd>A program used to open links to external websites, e.g. <strong>firefox</strong>, <strong>google-chrome</strong>, <strong>w3m</strong>, <strong>lynx</strong>, <strong>elinks</strong>
  <br/> <em>If not specified, will fallback to $BROWSER, or try to intelligently choose a browser supported by your system.</em></dd>
  
  <dt>$RTV_URLVIEWER</dt>
  <dd>A tool used to extract hyperlinks from blocks of text, e.g.<a href=https://github.com/sigpipe/urlview>urlview</a>, <a href=https://github.com/firecat53/urlscan>urlscan</a>
  <br/> <em>If not specified, will fallback to urlview if it is installed.</em></dd>
</dl>

### Copying to the Clipboard
RTV supports copying submission links to the OS clipboard.
On macOS this is supported out of the box.
On Linux systems you will need to install either [xsel](http://www.vergenet.net/~conrad/software/xsel/) or [xclip](https://sourceforge.net/projects/xclip/).

## FAQ

**Why am I getting an error during installation/when launching rtv?**

> If your distro ships with an older version of python 2.7 or python-requests,
> you may experience SSL errors or other package incompatibilities. The
> easiest way to fix this is to install rtv using python 3. If you
> don't already have pip3, see http://stackoverflow.com/a/6587528 for setup
> instructions. Then do
>
> ```bash
> $ sudo pip uninstall rtv
> $ sudo pip3 install -U rtv
> ```

**Why do I see garbled text like** ``M-b~@M-"`` **or** ``^@`` **?**

> This type of text usually shows up when python is unable to render
> unicode properly.
>    
> 1. Try starting RTV in ascii-only mode with ``rtv --ascii``
> 2. Make sure that the terminal/font that you're using supports unicode
> 3. Try [setting the LOCALE to utf-8](https://perlgeek.de/en/article/set-up-a-clean-utf8-environment)
> 4. Your python may have been built against the wrong curses library,
>    see [here](stackoverflow.com/questions/19373027) and
>    [here](https://bugs.python.org/issue4787) for more information
  
**How do I run the code directly from the repository?**

> This project is structured to be run as a python *module*. This means that
> you need to launch it using python's ``-m`` flag. See the example below, which
> assumes that you have cloned the repository into the directory **~/rtv_project**.
>
> ```bash
> $ cd ~/rtv_project
> $ python3 -m rtv
> ```

## Contributing
All feedback and suggestions are welcome, just post an issue!

Before writing any code, please read the [Contributor Guidelines](https://github.com/michael-lazar/rtv/blob/master/CONTRIBUTING.rst).

## License
This project is distributed under the [MIT](https://github.com/michael-lazar/rtv/blob/master/LICENSE) license.

<p align="center">
<img alt="title image" src="resources/retro_term.png"/>
</p>
   

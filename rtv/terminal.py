# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import time
import shlex
import codecs
import curses
import logging
import threading
import webbrowser
import subprocess
import curses.ascii
from curses import textpad
from multiprocessing import Process
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

import six
from kitchen.text.display import textual_width_chop

from . import exceptions, mime_parsers, content
from .theme import Theme, ThemeList
from .objects import LoadScreen

try:
    # Fix only needed for versions prior to python 3.6
    from mailcap_fix import mailcap
except ImportError:
    import mailcap

try:
    # Added in python 3.4+
    from html import unescape
except ImportError:
    from six.moves import html_parser
    unescape = html_parser.HTMLParser().unescape


_logger = logging.getLogger(__name__)


class Terminal(object):

    MIN_HEIGHT = 10
    MIN_WIDTH = 20

    # ASCII codes
    ESCAPE = 27
    RETURN = 10
    SPACE = 32

    def __init__(self, stdscr, config):

        self.stdscr = stdscr
        self.config = config
        self.loader = LoadScreen(self)
        self.theme = None  # Initialized by term.set_theme()
        self.theme_list = ThemeList()

        self._display = None
        self._mailcap_dict = mailcap.getcaps()
        self._term = os.environ.get('TERM')

        # This is a hack, the MIME parsers should be stateless
        # but we need to load the imgur credentials from the config
        mime_parsers.ImgurApiMIMEParser.CLIENT_ID = config['imgur_client_id']

    @property
    def up_arrow(self):
        return '^' if self.config['ascii'] else '▲'

    @property
    def down_arrow(self):
        return 'v' if self.config['ascii'] else '▼'

    @property
    def neutral_arrow(self):
        return 'o' if self.config['ascii'] else '•'

    @property
    def guilded(self):
        return '*' if self.config['ascii'] else '✪'

    @property
    def vline(self):
        return getattr(curses, 'ACS_VLINE', ord('|'))

    @property
    def display(self):
        """
        Use a number of methods to guess if the default webbrowser will open in
        the background as opposed to opening directly in the terminal.
        """

        if self._display is None:
            if sys.platform == 'darwin':
                # OS X won't set $DISPLAY unless xQuartz is installed.
                # If you're using OS X and you want to access a terminal
                # browser, you need to set it manually via $BROWSER.
                # See issue #166
                display = True
            else:
                display = bool(os.environ.get("DISPLAY"))

            # Use the convention defined here to parse $BROWSER
            # https://docs.python.org/2/library/webbrowser.html
            console_browsers = ['www-browser', 'links', 'links2', 'elinks',
                                'lynx', 'w3m']
            if "BROWSER" in os.environ:
                user_browser = os.environ["BROWSER"].split(os.pathsep)[0]
                if user_browser in console_browsers:
                    display = False
            if webbrowser._tryorder:
                if webbrowser._tryorder[0] in console_browsers:
                    display = False
            self._display = display
        return self._display

    def flash(self):
        """
        Flash the screen to indicate that an action was invalid.
        """
        if self.config['flash']:
            return curses.flash()
        else:
            return None

    @staticmethod
    def curs_set(val):
        """
        Change the cursor visibility, may fail for some terminals with limited
        cursor support.
        """
        try:
            curses.curs_set(val)
        except:
            pass

    @staticmethod
    def addch(window, y, x, ch, attr):
        """
        Curses addch() method that fixes a major bug in python 3.4.

        See http://bugs.python.org/issue21088
        """

        if sys.version_info[:3] == (3, 4, 0):
            y, x = x, y

        window.addch(y, x, ch, attr)

    def getch(self):
        """
        Wait for a keypress and return the corresponding character code (int).
        """
        return self.stdscr.getch()

    @staticmethod
    @contextmanager
    def suspend():
        """
        Suspend curses in order to open another subprocess in the terminal.
        """

        try:
            curses.endwin()
            yield
        finally:
            curses.doupdate()

    @contextmanager
    def no_delay(self):
        """
        Temporarily turn off character delay mode. In this mode, getch will not
        block while waiting for input and will return -1 if no key has been
        pressed.
        """

        try:
            self.stdscr.nodelay(1)
            yield
        finally:
            self.stdscr.nodelay(0)

    def get_arrow(self, likes):
        """
        Curses does define constants for symbols (e.g. curses.ACS_BULLET).
        However, they rely on using the curses.addch() function, which has been
        found to be buggy and a general PITA to work with. By defining them as
        unicode points they can be added via the more reliable curses.addstr().
        http://bugs.python.org/issue21088
        """

        if likes is None:
            return self.neutral_arrow, self.attr('NeutralVote')
        elif likes:
            return self.up_arrow, self.attr('Upvote')
        else:
            return self.down_arrow, self.attr('Downvote')

    def clean(self, string, n_cols=None):
        """
        Required reading!
            http://nedbatchelder.com/text/unipain.html

        Python 2 input string will be a unicode type (unicode code points).
        Curses will accept unicode if all of the points are in the ascii range.
        However, if any of the code points are not valid ascii curses will
        throw a UnicodeEncodeError: 'ascii' codec can't encode character,
        ordinal not in range(128). If we encode the unicode to a utf-8 byte
        string and pass that to curses, it will render correctly.

        Python 3 input string will be a string type (unicode code points).
        Curses will accept that in all cases. However, the n character count in
        addnstr will not be correct. If code points are passed to addnstr,
        curses will treat each code point as one character and will not account
        for wide characters. If utf-8 is passed in, addnstr will treat each
        'byte' as a single character.

        Reddit's api sometimes chokes and double-encodes some html characters
        Praw handles the initial decoding, but we need to do a second pass
        just to make sure. See https://github.com/michael-lazar/rtv/issues/96

        Example:
            &amp;amp; -> returned directly from reddit's api
            &amp;     -> returned after PRAW decodes the html characters
            &         -> returned after our second pass, this is the true value
        """

        if n_cols is not None and n_cols <= 0:
            return ''

        if isinstance(string, six.text_type):
            string = unescape(string)

        if self.config['ascii']:
            if isinstance(string, six.binary_type):
                string = string.decode('utf-8')
            string = string.encode('ascii', 'replace')
            return string[:n_cols] if n_cols else string
        else:
            if n_cols:
                string = textual_width_chop(string, n_cols)
            if isinstance(string, six.text_type):
                string = string.encode('utf-8')
            return string

    def add_line(self, window, text, row=None, col=None, attr=None):
        """
        Unicode aware version of curses's built-in addnstr method.

        Safely draws a line of text on the window starting at position
        (row, col). Checks the boundaries of the window and cuts off the text
        if it exceeds the length of the window.
        """

        # The following arg combos must be supported to conform with addnstr
        # (window, text)
        # (window, text, attr)
        # (window, text, row, col)
        # (window, text, row, col, attr)
        cursor_row, cursor_col = window.getyx()
        row = row if row is not None else cursor_row
        col = col if col is not None else cursor_col

        max_rows, max_cols = window.getmaxyx()
        n_cols = max_cols - col - 1
        if n_cols <= 0:
            # Trying to draw outside of the screen bounds
            return

        try:
            text = self.clean(text, n_cols)
            params = [] if attr is None else [attr]
            window.addstr(row, col, text, *params)
        except (curses.error, ValueError, TypeError) as e:
            # Curses handling of strings with invalid null bytes (b'\00')
            #   python 2: TypeError: "int,int,str"
            #   python 3: ValueError: "embedded null byte"
            _logger.warning('add_line raised an exception')
            _logger.exception(str(e))

    @staticmethod
    def add_space(window):
        """
        Shortcut for adding a single space to a window at the current position
        """

        row, col = window.getyx()
        _, max_cols = window.getmaxyx()
        n_cols = max_cols - col - 1
        if n_cols <= 0:
            # Trying to draw outside of the screen bounds
            return

        window.addstr(row, col, ' ')

    def show_notification(self, message, timeout=None, style='Info'):
        """
        Overlay a message box on the center of the screen and wait for input.

        Params:
            message (list or string): List of strings, one per line.
            timeout (float): Optional, maximum length of time that the message
                will be shown before disappearing.
            style (str): The theme element that will be applied to the
                notification window
        """

        assert style in ('Info', 'Warning', 'Error', 'Success')

        if isinstance(message, six.string_types):
            message = message.splitlines()

        n_rows, n_cols = self.stdscr.getmaxyx()
        v_offset, h_offset = self.stdscr.getbegyx()

        box_width = max(len(m) for m in message) + 2
        box_height = len(message) + 2

        # Cut off the lines of the message that don't fit on the screen
        box_width = min(box_width, n_cols)
        box_height = min(box_height, n_rows)
        message = message[:box_height - 2]

        s_row = (n_rows - box_height) // 2 + v_offset
        s_col = (n_cols - box_width) // 2 + h_offset

        window = curses.newwin(box_height, box_width, s_row, s_col)
        window.bkgd(str(' '), self.attr('Notice{0}'.format(style)))
        window.erase()
        window.border()

        for index, line in enumerate(message, start=1):
            self.add_line(window, line, index, 1)
        window.refresh()

        ch, start = -1, time.time()
        with self.no_delay():
            while timeout is None or time.time() - start < timeout:
                ch = self.getch()
                if ch != -1:
                    break
                time.sleep(0.01)

        window.clear()
        del window
        self.stdscr.touchwin()
        self.stdscr.refresh()

        return ch

    def open_link(self, url):
        """
        Open a media link using the definitions from the user's mailcap file.

        Most urls are parsed using their file extension, but special cases
        exist for websites that are prevalent on reddit such as Imgur and
        Gfycat. If there are no valid mailcap definitions, RTV will fall back
        to using the default webbrowser.

        RTV checks for certain mailcap fields to determine how to open a link:
            - If ``copiousoutput`` is specified, the curses application will
              be paused and stdout will be piped to the system pager.
            - If `needsterminal`` is specified, the curses application will
              yield terminal control to the subprocess until it has exited.
            - Otherwise, we assume that the subprocess is meant to open a new
              x-window, and we swallow all stdout output.

        Examples:
            Stream youtube videos with VLC
            Browse images and imgur albums with feh
            Watch .webm videos through your terminal with mplayer
            View images directly in your terminal with fbi or w3m
            Play .mp3 files with sox player
            Send HTML pages your pager using to html2text
            ...anything is possible!
        """

        if not self.config['enable_media']:
            self.open_browser(url)
            return

        try:
            with self.loader('Checking link', catch_exception=False):
                command, entry = self.get_mailcap_entry(url)
        except exceptions.MailcapEntryNotFound:
            self.open_browser(url)
            return

        _logger.info('Executing command: %s', command)
        needs_terminal = 'needsterminal' in entry
        copious_output = 'copiousoutput' in entry

        if needs_terminal or copious_output:
            # Blocking, pause rtv until the process returns
            with self.suspend():
                os.system('clear')
                p = subprocess.Popen(
                    [command], stderr=subprocess.PIPE,
                    universal_newlines=True, shell=True)
                _, stderr = p.communicate()
                if copious_output:
                    six.moves.input('Press any key to continue')
            code = p.poll()
            if code != 0:
                _logger.warning(stderr)
                self.show_notification(
                    'Program exited with status={0}\n{1}'.format(
                        code, stderr.strip()), style='Error')

        else:
            # Non-blocking, open a background process
            with self.loader('Opening page', delay=0):
                p = subprocess.Popen(
                    [command], shell=True, universal_newlines=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Wait a little while to make sure that the command doesn't
                # exit with an error. This isn't perfect, but it should be good
                # enough to catch invalid commands.
                time.sleep(1.0)
                code = p.poll()
                if code is not None and code != 0:
                    _, stderr = p.communicate()
                    raise exceptions.BrowserError(
                        'Program exited with status={0}\n{1}'.format(
                            code, stderr.strip()))

                # Spin off a thread with p.communicate() to avoid subprocess
                # hang when the stodout/stderr PIPE gets filled up. This
                # behavior was discovered when opening long gifs with mpv
                # because mpv sends a progress bar to stderr.
                # https://thraxil.org/users/anders/posts/2008/03/13/
                threading.Thread(target=p.communicate).start()

    def get_mailcap_entry(self, url):
        """
        Search through the mime handlers list and attempt to find the
        appropriate command to open the provided url with.

        Will raise a MailcapEntryNotFound exception if no valid command exists.

        Params:
            url (text): URL that will be checked

        Returns:
            command (text): The string of the command that should be executed
                in a subprocess to open the resource.
            entry (dict): The full mailcap entry for the corresponding command
        """

        for parser in mime_parsers.parsers:
            if parser.pattern.match(url):
                # modified_url may be the same as the original url, but it
                # could also be updated to point to a different page, or it
                # could refer to the location of a temporary file with the
                # page's downloaded content.
                try:
                    modified_url, content_type = parser.get_mimetype(url)
                except Exception as e:
                    # If Imgur decides to change its html layout, let it fail
                    # silently in the background instead of crashing.
                    _logger.warning('parser %s raised an exception', parser)
                    _logger.exception(e)
                    raise exceptions.MailcapEntryNotFound()
                if not content_type:
                    _logger.info('Content type could not be determined')
                    raise exceptions.MailcapEntryNotFound()
                elif content_type == 'text/html':
                    _logger.info('Content type text/html, deferring to browser')
                    raise exceptions.MailcapEntryNotFound()

                command, entry = mailcap.findmatch(
                    self._mailcap_dict, content_type, filename=modified_url)
                if not entry:
                    _logger.info('Could not find a valid mailcap entry')
                    raise exceptions.MailcapEntryNotFound()

                return command, entry

        # No parsers matched the url
        raise exceptions.MailcapEntryNotFound()

    def open_browser(self, url):
        """
        Open the given url using the default webbrowser. The preferred browser
        can specified with the $BROWSER environment variable. If not specified,
        python webbrowser will try to determine the default to use based on
        your system.

        For browsers requiring an X display, we open a new subprocess and
        redirect stdout/stderr to devnull. This is a workaround to stop
        BackgroundBrowsers (e.g. xdg-open, any BROWSER command ending in "&"),
        from spewing warning messages to the console. See
        http://bugs.python.org/issue22277 for a better description of the
        problem.

        For console browsers (e.g. w3m), RTV will suspend and display the
        browser window within the same terminal. This mode is triggered either
        when

        1. $BROWSER is set to a known console browser, or
        2. $DISPLAY is undefined, indicating that the terminal is running
           headless

        There may be other cases where console browsers are opened (xdg-open?)
        but are not detected here. These cases are still unhandled and will
        probably be broken if we incorrectly assume that self.display=True.
        """

        if self.display:
            with self.loader('Opening page in a new window'):

                def open_url_silent(url):
                    # This used to be done using subprocess.Popen().
                    # It was switched to multiprocessing.Process so that we
                    # can re-use the webbrowser instance that has been patched
                    # by RTV. It's also safer because it doesn't inject
                    # python code through the command line.

                    # Surpress stdout/stderr from the browser, see
                    # https://stackoverflow.com/questions/2323080. We can't
                    # depend on replacing sys.stdout & sys.stderr because
                    # webbrowser uses Popen().
                    stdout, stderr = os.dup(1), os.dup(2)
                    null = os.open(os.devnull, os.O_RDWR)
                    try:
                        os.dup2(null, 1)
                        os.dup2(null, 2)
                        webbrowser.open_new_tab(url)
                    finally:
                        null.close()
                        os.dup2(stdout, 1)
                        os.dup2(stderr, 2)

                p = Process(target=open_url_silent, args=(url,))
                p.start()
                # Give the browser 7 seconds to open a new tab. Because the
                # display is set, calling webbrowser should be non-blocking.
                # If it blocks or returns an error, something went wrong.
                try:
                    p.join(7)
                    if p.is_alive():
                        raise exceptions.BrowserError(
                            'Timeout waiting for browser to open')
                finally:
                    # This will be hit on the browser timeout, but also if the
                    # user presses the ESC key. We always want to kill the
                    # webbrowser process if it hasn't opened the tab and
                    # terminated by now.
                    try:
                        p.terminate()
                    except OSError:
                        pass
        else:
            with self.suspend():
                webbrowser.open_new_tab(url)

    def open_pager(self, data, wrap=None):
        """
        View a long block of text using the system's default pager.

        The data string will be piped directly to the pager.
        """

        pager = os.getenv('PAGER') or 'less'
        command = shlex.split(pager)

        if wrap:
            data_lines = content.Content.wrap_text(data, wrap)
            data = '\n'.join(data_lines)

        try:
            with self.suspend():
                _logger.debug('Running command: %s', command)
                p = subprocess.Popen(command, stdin=subprocess.PIPE)
                try:
                    p.communicate(data.encode('utf-8'))
                except KeyboardInterrupt:
                    p.terminate()
        except OSError as e:
            _logger.exception(e)
            self.show_notification('Could not open pager %s' % pager)

    @contextmanager
    def open_editor(self, data=''):
        """
        Open a file for editing using the system's default editor.

        After the file has been altered, the text will be read back and lines
        starting with '#' will be stripped. If an error occurs inside of the
        context manager, the file will be preserved. Otherwise, the file will
        be deleted when the context manager closes.

        Params:
            data (str): If provided, text will be written to the file before
                opening it with the editor.

        Returns:
            text (str): The text that the user entered into the editor.
        """

        with NamedTemporaryFile(prefix='rtv_', suffix='.txt', delete=False) as fp:
            # Create a tempory file and grab the name, but close immediately so
            # we can re-open using the right encoding
            filepath = fp.name

        with codecs.open(filepath, 'w', 'utf-8') as fp:
            fp.write(data)
        _logger.info('File created: %s', filepath)

        editor = (os.getenv('RTV_EDITOR') or
                  os.getenv('VISUAL') or
                  os.getenv('EDITOR') or
                  'nano')
        command = shlex.split(editor) + [filepath]
        try:
            with self.suspend():
                _logger.debug('Running command: %s', command)
                p = subprocess.Popen(command)
                try:
                    p.communicate()
                except KeyboardInterrupt:
                    p.terminate()
        except OSError as e:
            _logger.exception(e)
            self.show_notification('Could not open file with %s' % editor)

        with codecs.open(filepath, 'r', 'utf-8') as fp:
            text = ''.join(line for line in fp if not line.startswith('#'))
            text = text.rstrip()

        try:
            yield text
        except exceptions.TemporaryFileError:
            # All exceptions will cause the file to *not* be removed, but these
            # ones should also be swallowed
            _logger.info('Caught TemporaryFileError')
            self.show_notification('Post saved as: %s' % filepath)
        else:
            # If no errors occurred, try to remove the file
            try:
                os.remove(filepath)
            except OSError:
                _logger.warning('Could not delete: %s', filepath)
            else:
                _logger.info('File deleted: %s', filepath)

    def open_urlview(self, data):
        """
        Pipe a block of text to urlview, which displays a list of urls
        contained in the text and allows the user to open them with their
        web browser.
        """

        urlview = os.getenv('RTV_URLVIEWER') or 'urlview'
        command = shlex.split(urlview)
        try:
            with self.suspend():
                _logger.debug('Running command: %s', command)
                p = subprocess.Popen(command, stdin=subprocess.PIPE)
                try:
                    p.communicate(input=data.encode('utf-8'))
                except KeyboardInterrupt:
                    p.terminate()

                code = p.poll()
                if code == 1:
                    # Clear the "No URLs found." message from stdout
                    sys.stdout.write("\033[F")
                    sys.stdout.flush()

            if code == 1:
                self.show_notification('No URLs found')

        except OSError as e:
            _logger.exception(e)
            self.show_notification(
                'Failed to open {0}'.format(urlview))

    def text_input(self, window, allow_resize=False):
        """
        Transform a window into a text box that will accept user input and loop
        until an escape sequence is entered.

        If the escape key (27) is pressed, cancel the textbox and return None.
        Otherwise, the textbox will wait until it is full (^j, or a new line is
        entered on the bottom line) or the BEL key (^g) is pressed.
        """

        window.clear()

        # Set cursor mode to 1 because 2 doesn't display on some terminals
        self.curs_set(1)

        # Keep insert_mode off to avoid the recursion error described here
        # http://bugs.python.org/issue13051
        textbox = textpad.Textbox(window)
        textbox.stripspaces = 0

        def validate(ch):
            "Filters characters for special key sequences"
            if ch == self.ESCAPE:
                raise exceptions.EscapeInterrupt()
            if (not allow_resize) and (ch == curses.KEY_RESIZE):
                raise exceptions.EscapeInterrupt()
            # Fix backspace for iterm
            if ch == curses.ascii.DEL:
                ch = curses.KEY_BACKSPACE
            return ch

        # Wrapping in an exception block so that we can distinguish when the
        # user hits the return character from when the user tries to back out
        # of the input.
        try:
            out = textbox.edit(validate=validate)
            if isinstance(out, six.binary_type):
                out = out.decode('utf-8')
        except exceptions.EscapeInterrupt:
            out = None

        self.curs_set(0)
        return self.strip_textpad(out)

    def prompt_input(self, prompt, key=False):
        """
        Display a text prompt at the bottom of the screen.

        Params:
            prompt (string): Text prompt that will be displayed
            key (bool): If true, grab a single keystroke instead of a full
                        string. This can be faster than pressing enter for
                        single key prompts (e.g. y/n?)
        """

        n_rows, n_cols = self.stdscr.getmaxyx()
        v_offset, h_offset = self.stdscr.getbegyx()
        ch, attr = str(' '), self.attr('Prompt')
        prompt = self.clean(prompt, n_cols - 1)

        # Create a new window to draw the text at the bottom of the screen,
        # so we can erase it when we're done.
        s_row = v_offset + n_rows - 1
        s_col = h_offset
        prompt_win = curses.newwin(1, len(prompt) + 1, s_row, s_col)
        prompt_win.bkgd(ch, attr)
        self.add_line(prompt_win, prompt)
        prompt_win.refresh()

        # Create a separate window for text input
        s_col = h_offset + len(prompt)
        input_win = curses.newwin(1, n_cols - len(prompt), s_row, s_col)
        input_win.bkgd(ch, attr)
        input_win.refresh()

        if key:
            self.curs_set(1)
            ch = self.getch()
            # We can't convert the character to unicode, because it may return
            # Invalid values for keys that don't map to unicode characters,
            # e.g. F1
            text = ch if ch != self.ESCAPE else None
            self.curs_set(0)
        else:
            text = self.text_input(input_win)

        prompt_win.clear()
        input_win.clear()
        del prompt_win
        del input_win
        self.stdscr.touchwin()
        self.stdscr.refresh()

        return text

    def prompt_y_or_n(self, prompt):
        """
        Wrapper around prompt_input for simple yes/no queries.
        """

        ch = self.prompt_input(prompt, key=True)
        if ch in (ord('Y'), ord('y')):
            return True
        elif ch in (ord('N'), ord('n'), None):
            return False
        else:
            self.flash()
            return False

    @staticmethod
    def strip_textpad(text):
        """
        Attempt to intelligently strip excess whitespace from the output of a
        curses textpad.
        """

        if text is None:
            return text

        # Trivial case where the textbox is only one line long.
        if '\n' not in text:
            return text.rstrip()

        # Allow one space at the end of the line. If there is more than one
        # space, assume that a newline operation was intended by the user
        stack, current_line = [], ''
        for line in text.split('\n'):
            if line.endswith('  ') or not line:
                stack.append(current_line + line.rstrip())
                current_line = ''
            else:
                current_line += line
        stack.append(current_line)

        # Prune empty lines at the bottom of the textbox.
        for item in stack[::-1]:
            if not item:
                stack.pop()
            else:
                break

        out = '\n'.join(stack)
        return out

    def clear_screen(self):
        """
        In the beginning this always called touchwin(). However, a bug
        was discovered in tmux when TERM was set to `xterm-256color`, where
        only part of the screen got redrawn when scrolling. tmux automatically
        sets TERM to `screen-256color`, but many people choose to override
        this in their tmux.conf or .bashrc file which can cause issues.
        Using clearok() instead seems to fix the problem, with the trade off
        of slightly more expensive screen refreshes.

        Update: It was discovered that using clearok() introduced a
        separate bug for urxvt users in which their screen flashed when
        scrolling. Heuristics were added to make it work with as many
        configurations as possible. It's still not perfect
        (e.g. urxvt + xterm-256color) will screen flash, but it should
        work in all cases if the user sets their TERM correctly.

        Reference:
            https://github.com/michael-lazar/rtv/issues/343
            https://github.com/michael-lazar/rtv/issues/323
        """

        if self._term != 'xterm-256color':
            self.stdscr.touchwin()
        else:
            self.stdscr.clearok(True)

    def attr(self, element):
        """
        Shortcut for fetching the color + attribute code for an element.
        """
        # The theme must be initialized before calling this
        assert self.theme is not None

        return self.theme.get(element)

    @staticmethod
    def check_theme(theme):
        """
        Check if the given theme is compatible with the terminal
        """
        terminal_colors = curses.COLORS if curses.has_colors() else 0

        if theme.required_colors > terminal_colors:
            return False
        elif theme.required_color_pairs > curses.COLOR_PAIRS:
            return False
        else:
            return True

    def set_theme(self, theme=None):
        """
        Check that the terminal supports the provided theme, and applies
        the theme to the terminal if possible.

        If the terminal doesn't support the theme, this falls back to the
        default theme. The default theme only requires 8 colors so it
        should be compatible with any terminal that supports basic colors.
        """

        terminal_colors = curses.COLORS if curses.has_colors() else 0
        default_theme = Theme(use_color=bool(terminal_colors))

        if theme is None:
            theme = default_theme

        elif theme.required_color_pairs > curses.COLOR_PAIRS:
            _logger.warning(
                'Theme `%s` requires %s color pairs, but $TERM=%s only '
                'supports %s color pairs, switching to default theme',
                theme.name, theme.required_color_pairs, self._term,
                curses.COLOR_PAIRS)
            theme = default_theme

        elif theme.required_colors > terminal_colors:
            _logger.warning(
                'Theme `%s` requires %s colors, but $TERM=%s only '
                'supports %s colors, switching to default theme',
                theme.name, theme.required_colors, self._term,
                curses.COLORS)
            theme = default_theme

        theme.bind_curses()
        self.theme = theme

        # Apply the default color to the whole screen
        self.stdscr.bkgd(str(' '), self.attr('Normal'))

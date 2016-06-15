# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import time
import codecs
import curses
import mimetypes
import webbrowser
import subprocess
import curses.ascii
from curses import textpad
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

import six
from kitchen.text.display import textual_width_chop

from . import exceptions
from .objects import LoadScreen, Color

try:
    # Added in python 3.4+
    from html import unescape
except ImportError:
    from six.moves import html_parser
    unescape = html_parser.HTMLParser().unescape


class Terminal(object):

    MIN_HEIGHT = 10
    MIN_WIDTH = 20

    # ASCII code
    ESCAPE = 27
    RETURN = 10
    SPACE = 32

    def __init__(self, stdscr, config):

        self.stdscr = stdscr
        self.config = config
        self.ascii = self.config['ascii']
        self.loader = LoadScreen(self)
        self._display = None

    @property
    def up_arrow(self):
        symbol = '^' if self.ascii else '▲'
        attr = curses.A_BOLD | Color.GREEN
        return symbol, attr

    @property
    def down_arrow(self):
        symbol = 'v' if self.ascii else '▼'
        attr = curses.A_BOLD | Color.RED
        return symbol, attr

    @property
    def neutral_arrow(self):
        symbol = 'o' if self.ascii else '•'
        attr = curses.A_BOLD
        return symbol, attr

    @property
    def timestamp_sep(self):
        symbol = '-'
        attr = curses.A_BOLD
        return symbol, attr

    @property
    def guilded(self):
        symbol = '*' if self.ascii else '✪'
        attr = curses.A_BOLD | Color.YELLOW
        return symbol, attr

    @property
    def stickied(self):
        text = '[stickied]'
        attr = Color.GREEN
        return text, attr

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
                # OSX doesn't always set DISPLAY so we can't use this to check
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

    @staticmethod
    def flash():
        return curses.flash()

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
            return self.neutral_arrow
        elif likes:
            return self.up_arrow
        else:
            return self.down_arrow

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

        if self.ascii:
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

        text = self.clean(text, n_cols)
        params = [] if attr is None else [attr]
        window.addstr(row, col, text, *params)

    def show_notification(self, message, timeout=None):
        """
        Overlay a message box on the center of the screen and wait for input.

        Params:
            message (list or string): List of strings, one per line.
            timeout (float): Optional, maximum length of time that the message
                will be shown before disappearing.
        """

        if isinstance(message, six.string_types):
            message = [message]

        n_rows, n_cols = self.stdscr.getmaxyx()

        box_width = max(len(m) for m in message) + 2
        box_height = len(message) + 2

        # Cut off the lines of the message that don't fit on the screen
        box_width = min(box_width, n_cols)
        box_height = min(box_height, n_rows)
        message = message[:box_height-2]

        s_row = (n_rows - box_height) // 2
        s_col = (n_cols - box_width) // 2

        window = curses.newwin(box_height, box_width, s_row, s_col)
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

    def open_link(self, link):
        """Open a link with the appropriate handler."""
        mimetype, _ = mimetypes.guess_type(link)
        handler = self.config.handlers.get(mimetype)
        if handler is None:
            # Fall back to browser.
            self.open_browser(link)
        else:
            handler(self, link)

    def open_browser(self, url):
        """
        Open the given url using the default webbrowser. The preferred browser
        can specified with the $BROWSER environment variable. If not specified,
        python webbrowser will try to determine the default to use based on
        your system.

        For browsers requiring an X display, we call
        webbrowser.open_new_tab(url) and redirect stdout/stderr to devnull.
        This is a workaround to stop firefox from spewing warning messages to
        the console. See http://bugs.python.org/issue22277 for a better
        description of the problem.

        For console browsers (e.g. w3m), RTV will suspend and display the
        browser window within the same terminal. This mode is triggered either
        when

        1. $BROWSER is set to a known console browser, or
        2. $DISPLAY is undefined, indicating that the terminal is running
           headless

        There may be other cases where console browsers are opened (xdg-open?)
        but are not detected here.
        """

        if self.display:
            command = "import webbrowser; webbrowser.open_new_tab('%s')" % url
            args = [sys.executable, '-c', command]
            with self.loader('Opening page in a new window'), \
                    open(os.devnull, 'ab+', 0) as null:
                p = subprocess.Popen(args, stdout=null, stderr=null)
                # Give the browser 5 seconds to open a new tab. Because the
                # display is set, calling webbrowser should be non-blocking.
                # If it blocks or returns an error, something went wrong.
                try:
                    start = time.time()
                    while time.time() - start < 10:
                        code = p.poll()
                        if code == 0:
                            break  # Success
                        elif code is not None:
                            raise exceptions.BrowserError(
                                'Browser exited with status=%s' % code)
                        time.sleep(0.01)
                    else:
                        raise exceptions.BrowserError('Timeout opening browser')
                finally:
                    # Can't check the loader exception because the oauth module
                    # supersedes this loader and we need to always kill the
                    # process if escape is pressed
                    try:
                        p.terminate()
                    except OSError:
                        pass
        else:
            with self.suspend():
                webbrowser.open_new_tab(url)

    def open_pager(self, data):
        """
        View a long block of text using the system's default pager.

        The data string will be piped directly to the pager.
        """

        pager = os.getenv('PAGER') or 'less'
        try:
            with self.suspend():
                p = subprocess.Popen([pager], stdin=subprocess.PIPE)
                p.stdin.write(self.clean(data))
                p.stdin.close()
                try:
                    p.wait()
                except KeyboardInterrupt:
                    p.terminate()
        except OSError:
            self.show_notification('Could not open pager %s' % pager)

    def open_editor(self, data=''):
        """
        Open a temporary file using the system's default editor.

        The data string will be written to the file before opening. This
        function will block until the editor has closed. At that point the file
        will be read and and lines starting with '#' will be stripped.
        """

        with NamedTemporaryFile(prefix='rtv-', suffix='.txt', mode='wb') as fp:
            fp.write(self.clean(data))
            fp.flush()
            editor = os.getenv('RTV_EDITOR') or os.getenv('EDITOR') or 'nano'

            try:
                with self.suspend():
                    p = subprocess.Popen([editor, fp.name])
                    try:
                        p.wait()
                    except KeyboardInterrupt:
                        p.terminate()
            except OSError:
                self.show_notification('Could not open file with %s' % editor)

            # Open a second file object to read. This appears to be necessary
            # in order to read the changes made by some editors (gedit). w+
            # mode does not work!
            with codecs.open(fp.name, 'r', 'utf-8') as fp2:
                text = ''.join(line for line in fp2 if not line.startswith('#'))
                text = text.rstrip()
                return text

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
        curses.curs_set(1)

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

        curses.curs_set(0)
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
        attr = curses.A_BOLD | Color.CYAN
        prompt = self.clean(prompt, n_cols-1)

        # Create a new window to draw the text at the bottom of the screen,
        # so we can erase it when we're done.
        prompt_win = curses.newwin(1, len(prompt)+1, n_rows-1, 0)
        self.add_line(prompt_win, prompt, attr=attr)
        prompt_win.refresh()

        # Create a separate window for text input
        input_win = curses.newwin(1, n_cols-len(prompt), n_rows-1, len(prompt))
        input_win.attrset(attr)

        if key:
            curses.curs_set(1)
            ch = self.getch()
            # We can't convert the character to unicode, because it may return
            # Invalid values for keys that don't map to unicode characters,
            # e.g. F1
            text = ch if ch != self.ESCAPE else None
            curses.curs_set(0)
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
            if line.endswith('  '):
                stack.append(current_line + line.rstrip())
                current_line = ''
            else:
                current_line += line
        stack.append(current_line)

        # Prune empty lines at the bottom of the textbox.
        for item in stack[::-1]:
            if len(item) == 0:
                stack.pop()
            else:
                break

        out = '\n'.join(stack)
        return out

import os
import sys
import curses
import time
import threading
import subprocess
from curses import textpad, ascii
from contextlib import contextmanager
from functools import partial
from types import MethodType

from six.moves import configparser
from six import create_bound_method

from .errors import EscapePressed

ESCAPE = 27

HELP = """
Global Commands
  `UP/DOWN` or `j/k`  : Scroll to the prev/next item
  `r` or `F5`         : Refresh the current page
  `q`                 : Quit the program
  `o`                 : Open the selected item in the default web browser
  `?`                 : Show this help message

Subreddit Mode
  `RIGHT` or `l`      : View comments for the selected submission
  `/`                 : Open a prompt to switch subreddits

Submission Mode
  `LEFT` or `h`       : Return to subreddit mode
  `RIGHT` or `l`      : Fold the selected comment, or load additional comments
"""

class Color(object):

    COLORS = {
        'RED': (curses.COLOR_RED, -1),
        'GREEN': (curses.COLOR_GREEN, -1),
        'YELLOW': (curses.COLOR_YELLOW, -1),
        'BLUE': (curses.COLOR_BLUE, -1),
        'MAGENTA': (curses.COLOR_MAGENTA, -1),
        'CYAN': (curses.COLOR_CYAN, -1),
        'WHITE': (curses.COLOR_WHITE, -1),
        }

    @classmethod
    def get_level(cls, level):

        levels = [cls.MAGENTA, cls.CYAN, cls.GREEN, cls.YELLOW]
        return levels[level % len(levels)]

    @classmethod
    def init(cls):
        """
        Initialize color pairs inside of curses using the default background.

        This should be called once during the curses initial setup. Afterwards,
        curses color pairs can be accessed directly through class attributes.
        """

        # Assign the terminal's default (background) color to code -1
        curses.use_default_colors()

        for index, (attr, code) in enumerate(cls.COLORS.items(), start=1):
            curses.init_pair(index, code[0], code[1])
            setattr(cls, attr, curses.color_pair(index))

def load_config():
    """
    Search for a configuration file at the location ~/.rtv and attempt to load
    saved settings for things like the username and password.
    """

    config_path = os.path.join(os.path.expanduser('~'), '.rtv')
    config = configparser.ConfigParser()
    config.read(config_path)

    defaults = {}
    if config.has_section('rtv'):
        defaults = dict(config.items('rtv'))

    return defaults

def hide_stderr():
    """
    Redirect all stderr output to null. This is a hack to stop the webbrowser
    from spewing errors in firefox.
    """

    # http://www.thecodingforums.com/threads/how-to-change-redirect-stderr.355342/#post-1868822
    sys.stderr.flush()
    err = open(os.devnull, 'ab+', 0)
    os.dup2(err.fileno(), sys.stderr.fileno())

def text_input(window):
    """
    Transform a window into a text box that will accept user input and loop
    until an escape sequence is entered.

    If enter is pressed, return the input text as a string.
    If escape is pressed, return None.
    """

    window.clear()
    curses.curs_set(2)
    textbox = textpad.Textbox(window, insert_mode=True)

    def validate(ch):
        "Filters characters for special key sequences"

        if ch == ESCAPE:
            raise EscapePressed

        # Fix backspace for iterm
        if ch == ascii.DEL:
            ch = curses.KEY_BACKSPACE

        return ch

    # Wrapping in an exception block so that we can distinguish when the user
    # hits the return character from when the user tries to back out of the
    # input.
    try:
        out = textbox.edit(validate=validate)
        out = out.strip()
    except EscapePressed:
        out = None

    curses.curs_set(0)
    return out


def display_message(stdscr, message):
    "Display a message box at the center of the screen and wait for a keypress"

    n_rows, n_cols = stdscr.getmaxyx()

    box_width = max(map(len, message)) + 2
    box_height = len(message) + 2

    # Make sure the window is large enough to fit the message
    # TODO: Should find a better way to display the message in this situation
    if (box_width > n_cols) or (box_height > n_rows):
        curses.flash()
        return

    s_row = (n_rows - box_height) // 2
    s_col = (n_cols - box_width) // 2
    window = stdscr.derwin(box_height, box_width, s_row, s_col)

    window.erase()
    window.border()

    for index, line in enumerate(message, start=1):
        window.addstr(index, 1, line)

    window.refresh()
    stdscr.getch()

    window.clear()
    window = None
    stdscr.refresh()


def display_help(stdscr):
    """Display a help message box at the center of the screen and wait for a
    keypress"""

    help_msgs = HELP.split("\n")
    display_message(stdscr, help_msgs)


class LoadScreen(object):

    def __init__(self, stdscr):

        self._stdscr = stdscr

        self._args = None
        self._animator = None
        self._is_running = None

    def __call__(
            self,
            delay=0.5,
            interval=0.4,
            message='Downloading',
            trail='...'):

        self._args = (delay, interval, message, trail)
        return self

    def __enter__(self):

        self._animator = threading.Thread(target=self.animate, args=self._args)
        self._animator.daemon = True

        self._is_running = True
        self._animator.start()

    def __exit__(self, exc_type, exc_val, exc_tb):

        self._is_running = False
        self._animator.join()

    def animate(self, delay, interval, message, trail):

        # Delay before starting animation to avoid wasting resources if the
        # wait time is very short
        start = time.time()
        while (time.time() - start) < delay:
            if not self._is_running:
                return

        message_len = len(message) + len(trail)
        n_rows, n_cols = self._stdscr.getmaxyx()
        s_row = (n_rows - 3) // 2
        s_col = (n_cols - message_len - 1) // 2
        window = self._stdscr.derwin(3, message_len+2, s_row, s_col)

        while True:
            for i in range(len(trail)+1):

                if not self._is_running:
                    window.clear()
                    window = None
                    self._stdscr.refresh()
                    return

                window.erase()
                window.border()
                window.addstr(1, 1, message + trail[:i])
                window.refresh()
                time.sleep(interval)


@contextmanager
def curses_session():

    try:
        # Curses must wait for some time after the Escape key is pressed to
        # check if it is the beginning of an escape sequence indicating a
        # special key. The default wait time is 1 second, which means that
        # getch() will not return the escape key (27) until a full second
        # after it has been pressed.
        # Turn this down to 25 ms, which is close to what VIM uses.
        # http://stackoverflow.com/questions/27372068
        os.environ['ESCDELAY'] = '25'

        # Initialize curses
        stdscr = curses.initscr()

        # Turn off echoing of keys, and enter cbreak mode,
        # where no buffering is performed on keyboard input
        curses.noecho()
        curses.cbreak()

        # In keypad mode, escape sequences for special keys
        # (like the cursor keys) will be interpreted and
        # a special value like curses.KEY_LEFT will be returned
        stdscr.keypad(1)

        # Start color, too.  Harmless if the terminal doesn't have
        # color; user can test with has_color() later on.  The try/catch
        # works around a minor bit of over-conscientiousness in the curses
        # module -- the error return from C start_color() is ignorable.
        try:
            curses.start_color()
        except:
            pass

        Color.init()

        # Hide blinking cursor
        curses.curs_set(0)

        # hide_stderr()

        yield stdscr

    finally:

        if stdscr is not None:
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()

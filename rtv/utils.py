import os
import curses
import time
import threading
import subprocess
from curses import textpad, ascii
from contextlib import contextmanager
from functools import partial
from types import MethodType

from .errors import EscapePressed

ESCAPE = 27

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

def patch_popen():
    """
    Patch subprocess.Popen default behavior to redirect stdout + stderr to null.
    This is a hack to stop the webbrowser from spewing errors in firefox.
    """

    # http://stackoverflow.com/a/13359757/2526287
    stdout = open(os.devnull, 'w')
    func = partial(subprocess.Popen.__init__,
                   stdout=stdout, stderr=stdout, close_fds=True)
    subprocess.Popen.__init__ = MethodType(func, None, subprocess.Popen)

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

    message_len = len(message)
    n_rows, n_cols = stdscr.getmaxyx()
    s_row = (n_rows - 2) // 2
    s_col = (n_cols - message_len - 1) // 2
    window = stdscr.derwin(3, message_len+2, s_row, s_col)

    window.erase()
    window.border()
    window.addstr(1, 1, message)
    window.refresh()

    stdscr.getch()

    window.clear()
    window = None
    stdscr.refresh()


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
        s_row = (n_rows - 2) // 2
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
        # Curses must wait for some time after the Escape key is pressed to see
        # check if it is the beginning of an escape sequence indicating a
        # special key. The default wait time is 1 second, which means that
        # getch() will not return the escape key (27), until a full second
        # after it has been pressed. Turn this down to 25 ms, which is close to
        # what VIM uses.
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
        else:
            Color.init()

        # Hide blinking cursor
        curses.curs_set(0)

        # Breaks python3
        # patch_popen()

        yield stdscr

    finally:

        if stdscr is not None:
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()
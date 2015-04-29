import os
import time
import threading
import curses
from curses import textpad, ascii
from contextlib import contextmanager
from six.moves import configparser

from .docs import HELP
from .helpers import strip_textpad
from .exceptions import EscapeInterrupt
from .config import default_colors

__all__ = ['ESCAPE', 'UARROW', 'DARROW', 'BULLET', 'show_notification',
           'show_help', 'LoadScreen', 'Color', 'text_input', 'curses_session',
           'prompt_input']

ESCAPE = 27

# Curses does define constants for these (e.g. curses.ACS_BULLET)
# However, they rely on using the curses.addch() function, which has been
# found to be buggy and a PITA to work with. By defining them as unicode
# points they can be added via the more reliable curses.addstr().
# http://bugs.python.org/issue21088
UARROW = u'\u25b2'.encode('utf-8')
DARROW = u'\u25bc'.encode('utf-8')
BULLET = u'\u2022'.encode('utf-8')
GOLD = u'\u272A'.encode('utf-8')


def show_notification(stdscr, message):
    """
    Overlay a message box on the center of the screen and wait for user input.

    Params:
        message (list): List of strings, one per line.
    """

    n_rows, n_cols = stdscr.getmaxyx()

    box_width = max(map(len, message)) + 2
    box_height = len(message) + 2

    # Cut off the lines of the message that don't fit on the screen
    box_width = min(box_width, n_cols)
    box_height = min(box_height, n_rows)
    message = message[:box_height-2]

    s_row = (n_rows - box_height) // 2
    s_col = (n_cols - box_width) // 2

    window = stdscr.derwin(box_height, box_width, s_row, s_col)
    window.erase()
    window.border()

    for index, line in enumerate(message, start=1):
        window.addnstr(index, 1, line, box_width - 2)
    window.refresh()
    ch = stdscr.getch()

    window.clear()
    window = None
    stdscr.refresh()

    return ch


def show_help(stdscr):
    """
    Overlay a message box with the help screen.
    """

    show_notification(stdscr, HELP.splitlines())


class LoadScreen(object):

    """
    Display a loading dialog while waiting for a blocking action to complete.

    This class spins off a seperate thread to animate the loading screen in the
    background.

    Usage:
        #>>> loader = LoadScreen(stdscr)
        #>>> with loader(...):
        #>>>     blocking_request(...)
    """

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
        """
        Params:
            delay (float): Length of time that the loader will wait before
                printing on the screen. Used to prevent flicker on pages that
                load very fast.
            interval (float): Length of time between each animation frame.
            message (str): Message to display
            trail (str): Trail of characters that will be animated by the
                loading screen.
        """

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

        start = time.time()
        while (time.time() - start) < delay:
            if not self._is_running:
                return

        message_len = len(message) + len(trail)
        n_rows, n_cols = self._stdscr.getmaxyx()
        s_row = (n_rows - 3) // 2
        s_col = (n_cols - message_len - 1) // 2
        window = self._stdscr.derwin(3, message_len + 2, s_row, s_col)

        while True:
            for i in range(len(trail) + 1):

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


class Color(object):

    """
    Color attributes for curses.
    """

    _colors = {
        'RED': (curses.COLOR_RED, -1),
        'GREEN': (curses.COLOR_GREEN, -1),
        'YELLOW': (curses.COLOR_YELLOW, -1),
        'BLUE': (curses.COLOR_BLUE, -1),
        'MAGENTA': (curses.COLOR_MAGENTA, -1),
        'CYAN': (curses.COLOR_CYAN, -1),
        'WHITE': (curses.COLOR_WHITE, -1)
    }

    @classmethod
    def init(cls):
        """
        Initialize color pairs inside of curses using the default background.

        This should be called once during the curses initial setup. Afterwards,
        curses color pairs can be accessed directly through class attributes.
        """

        # Assign the terminal's default (background) color to code -1
        curses.use_default_colors()

        # Set default colors
        cls._colors.update( default_colors )
        # Override default colors by template
        cls._colors.update( cls.load_colors() )

        for index, (attr, code) in enumerate(cls._colors.items(), start=1):
            curses.init_pair(index, code[0], code[1])
            setattr(cls, attr, curses.color_pair(index))

    @classmethod
    def load_colors(cls):
        config = configparser.ConfigParser()
        # preserves upcase
        config.optionxform = str

        HOME = os.path.expanduser('~')
        XDG_CONFIG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
        config_paths = [
            os.path.join(XDG_CONFIG_HOME, 'rtv', 'rtv-colors.cfg'),
            os.path.join(HOME, '.rtv')
        ]

        # read only the first existing config file
        for config_path in config_paths:
            if os.path.exists(config_path):
                config.read(config_path)
                break

        params = {}
        if config.has_section('rtv-colors'):
            params = dict(config.items('rtv-colors'))

        colors = {}
        for key in params:
            colors[ key ] = tuple( [ int( v ) for v in params[ key ].strip().split(',') ] )

        return colors

    @classmethod
    def get_level(cls, level):

        levels = [cls.MAGENTA, cls.CYAN, cls.GREEN, cls.YELLOW]
        return levels[level % len(levels)]


def text_input(window, allow_resize=True):
    """
    Transform a window into a text box that will accept user input and loop
    until an escape sequence is entered.

    If enter is pressed, return the input text as a string.
    If escape is pressed, return None.
    """

    window.clear()

    # Set cursor mode to 1 because 2 doesn't display on some terminals
    curses.curs_set(1)

    # Turn insert_mode off to avoid the recursion error described here
    # http://bugs.python.org/issue13051
    textbox = textpad.Textbox(window, insert_mode=False)
    textbox.stripspaces = 0

    def validate(ch):
        "Filters characters for special key sequences"
        if ch == ESCAPE:
            raise EscapeInterrupt
        if (not allow_resize) and (ch == curses.KEY_RESIZE):
            raise EscapeInterrupt
        # Fix backspace for iterm
        if ch == ascii.DEL:
            ch = curses.KEY_BACKSPACE
        return ch

    # Wrapping in an exception block so that we can distinguish when the user
    # hits the return character from when the user tries to back out of the
    # input.
    try:
        out = textbox.edit(validate=validate)
    except EscapeInterrupt:
        out = None

    curses.curs_set(0)
    return strip_textpad(out)


def prompt_input(window, prompt, hide=False):
    """
    Display a prompt where the user can enter text at the bottom of the screen

    Set hide to True to make the input text invisible.
    """

    attr = curses.A_BOLD | Color.CYAN
    n_rows, n_cols = window.getmaxyx()

    if hide:
        prompt += ' ' * (n_cols - len(prompt) - 1)
        window.addstr(n_rows-1, 0, prompt, attr)
        out = window.getstr(n_rows-1, 1)
    else:
        window.addstr(n_rows - 1, 0, prompt, attr)
        window.refresh()
        subwin = window.derwin(1, n_cols - len(prompt),
                                   n_rows - 1, len(prompt))
        subwin.attrset(attr)
        out = text_input(subwin)

    return out


@contextmanager
def curses_session():
    """
    Setup terminal and initialize curses.
    """

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

        yield stdscr

    finally:

        if stdscr is not None:
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()

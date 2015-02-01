import os
import curses
import time
import threading
from curses import textpad
from contextlib import contextmanager

class EscapePressed(Exception):
    pass

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
        if ch == 27:
            raise EscapePressed
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
        s_row = (n_rows - 2) / 2
        s_col = (n_cols - message_len - 1) / 2
        window = self._stdscr.derwin(3, message_len+2, s_row, s_col)

        while True:
            for i in xrange(len(trail)+1):

                if not self._is_running:
                    # TODO: figure out why this isn't removing the screen
                    del window
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
        # getch() will not return the escape key (ord(27)), until a full second
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

            # Assign the terminal's default (background) color to code -1
            curses.use_default_colors()
        except:
            pass

        # Hide blinking cursor
        curses.curs_set(0)

        # Initialize color pairs - colored text on the default background
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)

        yield stdscr

    finally:

        if stdscr is not None:
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()
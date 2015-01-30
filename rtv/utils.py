from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import curses
from curses import textpad

class EscapePressed(Exception):
    pass


def clean(unicode_string):
    """
    Convert unicode string into ascii-safe characters.
    """

    return unicode_string.encode('ascii', 'replace').replace('\\', '')


def strip_subreddit_url(permalink):
    """
    Grab the subreddit from the permalink because submission.subreddit.url
    makes a seperate call to the API.
    """

    subreddit = clean(permalink).split('/')[4]
    return '/r/{}'.format(subreddit)


def humanize_timestamp(utc_timestamp, verbose=False):
    """
    Convert a utc timestamp into a human readable relative-time.
    """

    timedelta = datetime.utcnow() - datetime.utcfromtimestamp(utc_timestamp)

    seconds = int(timedelta.total_seconds())
    if seconds < 60:
        return 'moments ago' if verbose else '0min'
    minutes = seconds / 60
    if minutes < 60:
        return ('%d minutes ago' % minutes) if verbose else ('%dmin' % minutes)
    hours = minutes / 60
    if hours < 24:
        return ('%d hours ago' % hours) if verbose else ('%dhr' % hours)
    days = hours / 24
    if days < 30:
        return ('%d days ago' % days) if verbose else ('%dday' % days)
    months = days / 30.4
    if months < 12:
        return ('%d months ago' % months) if verbose else ('%dmonth' % months)
    years = months / 12
    return ('%d years ago' % years) if verbose else ('%dyr' % years)


def validate(ch):
    "Filters characters for special key sequences"
    if ch == 27:
        raise EscapePressed
    return ch

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
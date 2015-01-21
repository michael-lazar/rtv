from datetime import datetime, timedelta
import curses
from contextlib import contextmanager

@contextmanager
def curses_session():

    try:
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

def humanize_timestamp(utc_timestamp, long=True):
    """
    Convert a utc timestamp into a human readable time relative to now.
    """
    timedelta = datetime.utcnow() - datetime.utcfromtimestamp(utc_timestamp)
    seconds = int(timedelta.total_seconds())
    if seconds < 60:
        return 'moments ago' if long else '0min'
    minutes = seconds / 60
    if minutes < 60:
        return '%d' % minutes + (' minutes ago' if long else 'min')
    hours = minutes / 60
    if hours < 24:
        return '%d' % hours + (' hours ago' if long else 'hr')
    days = hours / 24
    if days < 30:
        return '%d' % days + (' days ago' if long else 'day')
    months = days / 30.4
    if months < 12:
        return '%d' % months + (' months ago' if long else 'month')
    years = months / 12
    return '%d' % years + (' years ago' if long else 'yr')


def flatten_tree(tree):
    """
    Flatten a PRAW comment tree while preserving the nested level of each
    comment via the `nested_level` attribute.
    """

    stack = tree[:]
    for item in stack:
        item.nested_level = 0

    retval = []
    while stack:
        item = stack.pop(0)
        nested = getattr(item, 'replies', None)
        if nested:
            for n in nested:
                n.nested_level = item.nested_level + 1
            stack[0:0] = nested
        retval.append(item)
    return retval


def clean(unicode_string):
    "Convert unicode string into ascii-safe characters."
    return unicode_string.encode('ascii', 'replace').replace('\\', '')
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import time
import curses
import signal
import inspect
import weakref
import logging
import threading
from contextlib import contextmanager

import six
import praw
import requests

from . import exceptions


_logger = logging.getLogger(__name__)


@contextmanager
def curses_session():
    """
    Setup terminal and initialize curses. Most of this copied from
    curses.wrapper in order to convert the wrapper into a context manager.
    """

    try:
        # Curses must wait for some time after the Escape key is pressed to
        # check if it is the beginning of an escape sequence indicating a
        # special key. The default wait time is 1 second, which means that
        # http://stackoverflow.com/questions/27372068
        os.environ['ESCDELAY'] = '25'

        # Initialize curses
        stdscr = curses.initscr()

        # Turn off echoing of keys, and enter cbreak mode, where no buffering
        # is performed on keyboard input
        curses.noecho()
        curses.cbreak()

        # In keypad mode, escape sequences for special keys (like the cursor
        # keys) will be interpreted and a special value like curses.KEY_LEFT
        # will be returned
        stdscr.keypad(1)

        # Start color, too.  Harmless if the terminal doesn't have color; user
        # can test with has_color() later on.  The try/catch works around a
        # minor bit of over-conscientiousness in the curses module -- the error
        # return from C start_color() is ignorable.
        try:
            curses.start_color()
        except:
            pass

        # Hide the blinking cursor
        curses.curs_set(0)

        Color.init()

        yield stdscr

    finally:
        if 'stdscr' in locals():
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()


class LoadScreen(object):
    """
    Display a loading dialog while waiting for a blocking action to complete.

    This class spins off a separate thread to animate the loading screen in the
    background. The loading thread also takes control of stdscr.getch(). If
    an exception occurs in the main thread while the loader is active, the
    exception will be caught, attached to the loader object, and displayed as
    a notification. The attached exception can be used to trigger context
    sensitive actions. For example, if the connection hangs while opening a
    submission, the user may press ctrl-c to raise a KeyboardInterrupt. In this
    case we would *not* want to refresh the current page.

    >>> with self.terminal.loader(...) as loader:
    >>>     # Perform a blocking request to load content
    >>>     blocking_request(...)
    >>>
    >>> if loader.exception is None:
    >>>     # Only run this if the load was successful
    >>>     self.refresh_content()

    When a loader is nested inside of itself, the outermost loader takes
    priority and all of the nested loaders become no-ops. Call arguments given
    to nested loaders will be ignored, and errors will propagate to the parent.

    >>> with self.terminal.loader(...) as loader:
    >>>
    >>>     # Additional loaders will be ignored
    >>>     with self.terminal.loader(...):
    >>>         raise KeyboardInterrupt()
    >>>
    >>>     # This code will not be executed because the inner loader doesn't
    >>>     # catch the exception
    >>>     assert False
    >>>
    >>> # The exception is finally caught by the outer loader
    >>> assert isinstance(terminal.loader.exception, KeyboardInterrupt)
    """

    EXCEPTION_MESSAGES = [
        (exceptions.RTVError, '{0}'),
        (praw.errors.OAuthException, 'Not logged in'),
        (praw.errors.OAuthScopeRequired, 'Not logged in'),
        (praw.errors.LoginRequired, 'Not logged in'),
        (praw.errors.InvalidCaptcha, 'Error, captcha required'),
        (praw.errors.PRAWException, '{0.__class__.__name__}'),
        (requests.exceptions.RequestException, '{0.__class__.__name__}'),
    ]

    def __init__(self, terminal):

        self.exception = None
        self.catch_exception = None
        self.depth = 0
        self._terminal = weakref.proxy(terminal)
        self._args = None
        self._animator = None
        self._is_running = None

    def __call__(
            self,
            message='Downloading',
            trail='...',
            delay=0.5,
            interval=0.4,
            catch_exception=True):
        """
        Params:
            delay (float): Length of time that the loader will wait before
                printing on the screen. Used to prevent flicker on pages that
                load very fast.
            interval (float): Length of time between each animation frame.
            message (str): Message to display
            trail (str): Trail of characters that will be animated by the
                loading screen.
            catch_exception (bool): If an exception occurs while the loader is
                active, this flag determines whether it is caught or allowed to
                bubble up.
        """

        if self.depth > 0:
            return self

        self.exception = None
        self.catch_exception = catch_exception
        self._args = (delay, interval, message, trail)
        return self

    def __enter__(self):

        self.depth += 1
        if self.depth > 1:
            return self

        self._animator = threading.Thread(target=self.animate, args=self._args)
        self._animator.daemon = True
        self._is_running = True
        self._animator.start()
        return self

    def __exit__(self, exc_type, e, exc_tb):

        self.depth -= 1
        if self.depth > 0:
            return

        self._is_running = False
        self._animator.join()

        if e is None or not self.catch_exception:
            # Skip exception handling
            return

        self.exception = e
        exc_name = type(e).__name__
        _logger.info('Loader caught: {0} - {1}'.format(exc_name, e))

        if isinstance(e, KeyboardInterrupt):
            # Don't need to print anything for this one, just swallow it
            return True

        for e_type, message in self.EXCEPTION_MESSAGES:
            # Some exceptions we want to swallow and display a notification
            if isinstance(e, e_type):
                self._terminal.show_notification(message.format(e))
                return True

    def animate(self, delay, interval, message, trail):

        # The animation starts with a configurable delay before drawing on the
        # screen. This is to prevent very short loading sections from
        # flickering on the screen before immediately disappearing.
        with self._terminal.no_delay():
            start = time.time()
            while (time.time() - start) < delay:
                # Pressing escape triggers a keyboard interrupt
                if self._terminal.getch() == self._terminal.ESCAPE:
                    os.kill(os.getpid(), signal.SIGINT)
                    self._is_running = False

                if not self._is_running:
                    return
                time.sleep(0.01)

        # Build the notification window
        message_len = len(message) + len(trail)
        n_rows, n_cols = self._terminal.stdscr.getmaxyx()
        s_row = (n_rows - 3) // 2
        s_col = (n_cols - message_len - 1) // 2
        window = curses.newwin(3, message_len + 2, s_row, s_col)

        # Animate the loading prompt until the stopping condition is triggered
        # when the context manager exits.
        with self._terminal.no_delay():
            while True:
                for i in range(len(trail) + 1):
                    if not self._is_running:
                        window.erase()
                        del window
                        self._terminal.stdscr.touchwin()
                        self._terminal.stdscr.refresh()
                        return

                    window.erase()
                    window.border()
                    self._terminal.add_line(window, message + trail[:i], 1, 1)
                    window.refresh()

                    # Break up the designated sleep interval into smaller
                    # chunks so we can more responsively check for interrupts.
                    for _ in range(int(interval/0.01)):
                        # Pressing escape triggers a keyboard interrupt
                        if self._terminal.getch() == self._terminal.ESCAPE:
                            os.kill(os.getpid(), signal.SIGINT)
                            self._is_running = False
                            break
                        time.sleep(0.01)


class Color(object):

    """
    Color attributes for curses.
    """

    RED = curses.A_NORMAL
    GREEN = curses.A_NORMAL
    YELLOW = curses.A_NORMAL
    BLUE = curses.A_NORMAL
    MAGENTA = curses.A_NORMAL
    CYAN = curses.A_NORMAL
    WHITE = curses.A_NORMAL

    _colors = {
        'RED': (curses.COLOR_RED, -1),
        'GREEN': (curses.COLOR_GREEN, -1),
        'YELLOW': (curses.COLOR_YELLOW, -1),
        'BLUE': (curses.COLOR_BLUE, -1),
        'MAGENTA': (curses.COLOR_MAGENTA, -1),
        'CYAN': (curses.COLOR_CYAN, -1),
        'WHITE': (curses.COLOR_WHITE, -1),
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

        for index, (attr, code) in enumerate(cls._colors.items(), start=1):
            curses.init_pair(index, code[0], code[1])
            setattr(cls, attr, curses.color_pair(index))

    @classmethod
    def get_level(cls, level):

        levels = [cls.MAGENTA, cls.CYAN, cls.GREEN, cls.YELLOW]
        return levels[level % len(levels)]


class Navigator(object):
    """
    Handles the math behind cursor movement and screen paging.

    This class determines how cursor movements effect the currently displayed
    page. For example, if scrolling down the page, items are drawn from the
    bottom up. This ensures that the item at the very bottom of the screen
    (the one selected by cursor) will be fully drawn and not cut off. Likewise,
    when scrolling up the page, items are drawn from the top down. If the
    cursor is moved around without hitting the top or bottom of the screen, the
    current mode is preserved.
    """

    def __init__(
            self,
            valid_page_cb,
            page_index=0,
            cursor_index=0,
            inverted=False):
        """
        Params:
            valid_page_callback (func): This function, usually `Content.get`,
                takes a page index and raises an IndexError if that index falls
                out of bounds. This is used to determine the upper and lower
                bounds of the page, i.e. when to stop scrolling.
            page_index (int): Initial page index.
            cursor_index (int): Initial cursor index, relative to the page.
            inverted (bool): Whether the page scrolling is reversed of not.
                normal - The page is drawn from the top of the screen,
                    starting with the page index, down to the bottom of
                    the screen.
                inverted - The page is drawn from the bottom of the screen,
                    starting with the page index, up to the top of the
                    screen.
        """

        self.page_index = page_index
        self.cursor_index = cursor_index
        self.inverted = inverted
        self._page_cb = valid_page_cb

    @property
    def step(self):
        return 1 if not self.inverted else -1

    @property
    def position(self):
        return self.page_index, self.cursor_index, self.inverted

    @property
    def absolute_index(self):
        """
        Return the index of the currently selected item.
        """

        return self.page_index + (self.step * self.cursor_index)

    def move(self, direction, n_windows):
        """
        Move the cursor up or down by the given increment.

        Params:
            direction (int): `1` will move the cursor down one item and `-1`
                will move the cursor up one item.
            n_windows (int): The number of items that are currently being drawn
                on the screen.

        Returns:
            valid (bool): Indicates whether or not the attempted cursor move is
                allowed. E.g. When the cursor is on the last comment,
                attempting to scroll down any further would not be valid.
            redraw (bool): Indicates whether or not the screen needs to be
                redrawn.
        """

        assert direction in (-1, 1)

        valid, redraw = True, False
        forward = ((direction * self.step) > 0)

        if forward:
            if self.page_index < 0:
                if self._is_valid(0):
                    # Special case - advance the page index if less than zero
                    self.page_index = 0
                    self.cursor_index = 0
                    redraw = True
                else:
                    valid = False
            else:
                self.cursor_index += 1
                if not self._is_valid(self.absolute_index):
                    # Move would take us out of bounds
                    self.cursor_index -= 1
                    valid = False
                elif self.cursor_index >= (n_windows - 1):
                    # Flip the orientation and reset the cursor
                    self.flip(self.cursor_index)
                    self.cursor_index = 0
                    redraw = True
        else:
            if self.cursor_index > 0:
                self.cursor_index -= 1
            else:
                self.page_index -= self.step
                if self._is_valid(self.absolute_index):
                    # We have reached the beginning of the page - move the
                    # index
                    redraw = True
                else:
                    self.page_index += self.step
                    valid = False  # Revert

        return valid, redraw

    def move_page(self, direction, n_windows):
        """
        Move the page down (positive direction) or up (negative direction).

        Paging down:
            The post on the bottom of the page becomes the post at the top of
            the page and the cursor is moved to the top.
        Paging up:
            The post at the top of the page becomes the post at the bottom of
            the page and the cursor is moved to the bottom.
        """

        assert direction in (-1, 1)
        assert n_windows >= 0

        # top of subreddit/submission page or only one
        # submission/reply on the screen: act as normal move
        if (self.absolute_index < 0) | (n_windows == 0):
            valid, redraw = self.move(direction, n_windows)
        else:
            # first page
            if self.absolute_index < n_windows and direction < 0:
                self.page_index = -1
                self.cursor_index = 0
                self.inverted = False

                # not submission mode: starting index is 0
                if not self._is_valid(self.absolute_index):
                    self.page_index = 0
                valid = True
            else:
                # flip to the direction of movement
                if ((direction > 0) & (self.inverted is True))\
                   | ((direction < 0) & (self.inverted is False)):
                    self.page_index += (self.step * (n_windows-1))
                    self.inverted = not self.inverted
                    self.cursor_index \
                        = (n_windows-(direction < 0)) - self.cursor_index

                valid = False
                adj = 0
                # check if reached the bottom
                while not valid:
                    n_move = n_windows - adj
                    if n_move == 0:
                        break

                    self.page_index += n_move * direction
                    valid = self._is_valid(self.absolute_index)
                    if not valid:
                        self.page_index -= n_move * direction
                        adj += 1

            redraw = True

        return valid, redraw

    def flip(self, n_windows):
        """
        Flip the orientation of the page.
        """

        assert n_windows >= 0
        self.page_index += (self.step * n_windows)
        self.cursor_index = n_windows
        self.inverted = not self.inverted

    def _is_valid(self, page_index):
        """
        Check if a page index will cause entries to fall outside valid range.
        """

        try:
            self._page_cb(page_index)
        except IndexError:
            return False
        else:
            return True


class Controller(object):
    """
    Event handler for triggering functions with curses keypresses.

    Register a keystroke to a class method using the @register decorator.
    >>> @Controller.register('a', 'A')
    >>> def func(self, *args)
    >>>     ...

    Register a default behavior by using `None`.
    >>> @Controller.register(None)
    >>> def default_func(self, *args)
    >>>     ...

    Bind the controller to a class instance and trigger a key. Additional
    arguments will be passed to the function.
    >>> controller = Controller(self)
    >>> controller.trigger('a', *args)
    """

    character_map = {}

    def __init__(self, instance):

        self.instance = instance
        # Build a list of parent controllers that follow the object's MRO to
        # check if any parent controllers have registered the keypress
        self.parents = inspect.getmro(type(self))[:-1]

    def trigger(self, char, *args, **kwargs):

        if isinstance(char, six.string_types) and len(char) == 1:
            char = ord(char)

        func = None
        # Check if the controller (or any of the controller's parents) have
        # registered a function to the given key
        for controller in self.parents:
            if func:
                break
            func = controller.character_map.get(char)
        # If the controller has not registered the key, check if there is a
        # default function registered
        for controller in self.parents:
            if func:
                break
            func = controller.character_map.get(None)
        return func(self.instance, *args, **kwargs) if func else None

    def bind(self, f, char):
        if isinstance(char, six.string_types) and len(char) == 1:
            self.character_map[ord(char)] = f
        else:
            self.character_map[char] = f

    @classmethod
    def register(cls, *chars):
        def inner(f):
            for char in chars:
                cls.bind(cls, f, char)
            return f
        return inner
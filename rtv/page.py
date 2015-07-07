import curses
import time
import six
import sys
import logging

import praw.errors
import requests
from kitchen.text.display import textual_width

from .helpers import open_editor
from .curses_helpers import (Color, show_notification, show_help, prompt_input,
                             add_line)
from .docs import COMMENT_EDIT_FILE, SUBMISSION_FILE

__all__ = ['Navigator', 'BaseController', 'BasePage']
_logger = logging.getLogger(__name__)


class Navigator(object):
    """
    Handles math behind cursor movement and screen paging.
    """

    def __init__(
            self,
            valid_page_cb,
            page_index=0,
            cursor_index=0,
            inverted=False):

        self.page_index = page_index
        self.cursor_index = cursor_index
        self.inverted = inverted
        self._page_cb = valid_page_cb
        self._header_window = None
        self._content_window = None

    @property
    def step(self):
        return 1 if not self.inverted else -1

    @property
    def position(self):
        return (self.page_index, self.cursor_index, self.inverted)

    @property
    def absolute_index(self):
        return self.page_index + (self.step * self.cursor_index)

    def move(self, direction, n_windows):
        "Move the cursor down (positive direction) or up (negative direction)"

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
        Move page down (positive direction) or up (negative direction).
        """

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
                        = (n_windows-(direction<0)) - self.cursor_index

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
        "Flip the orientation of the page"

        self.page_index += (self.step * n_windows)
        self.cursor_index = n_windows
        self.inverted = not self.inverted

    def _is_valid(self, page_index):
        "Check if a page index will cause entries to fall outside valid range"

        try:
            self._page_cb(page_index)
        except IndexError:
            return False
        else:
            return True


class SafeCaller(object):

    def __init__(self, window):
        self.window = window
        self.catch = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, e, exc_tb):

        if self.catch:
            if isinstance(e, praw.errors.APIException):
                message = ['Error: {}'.format(e.error_type), e.message]
                show_notification(self.window, message)
                _logger.exception(e)
                return True
            elif isinstance(e, praw.errors.ClientException):
                message = ['Error: Client Exception', e.message]
                show_notification(self.window, message)
                _logger.exception(e)
                return True
            elif isinstance(e, requests.HTTPError):
                show_notification(self.window, ['Unexpected Error'])
                _logger.exception(e)
                return True
            elif isinstance(e, requests.ConnectionError):
                show_notification(self.window, ['Unexpected Error'])
                _logger.exception(e)
                return True


class BaseController(object):
    """
    Event handler for triggering functions with curses keypresses.

    Register a keystroke to a class method using the @egister decorator.
    #>>> @Controller.register('a', 'A')
    #>>> def func(self, *args)

    Register a default behavior by using `None`.
    #>>> @Controller.register(None)
    #>>> def default_func(self, *args)

    Bind the controller to a class instance and trigger a key. Additional
    arguments will be passed to the function.
    #>>> controller = Controller(self)
    #>>> controller.trigger('a', *args)
    """

    character_map = {None: (lambda *args, **kwargs: None)}

    def __init__(self, instance):
        self.instance = instance

    def trigger(self, char, *args, **kwargs):

        if isinstance(char, six.string_types) and len(char) == 1:
            char = ord(char)

        func = self.character_map.get(char)
        if func is None:
            func = BaseController.character_map.get(char)
        if func is None:
            func = self.character_map.get(None)
        if func is None:
            func = BaseController.character_map.get(None)
        return func(self.instance, *args, **kwargs)

    @classmethod
    def register(cls, *chars):
        def wrap(f):
            for char in chars:
                if isinstance(char, six.string_types) and len(char) == 1:
                    cls.character_map[ord(char)] = f
                else:
                    cls.character_map[char] = f
            return f
        return wrap


class BasePage(object):
    """
    Base terminal viewer incorperates a cursor to navigate content
    """

    MIN_HEIGHT = 10
    MIN_WIDTH = 20

    def __init__(self, stdscr, reddit, content, **kwargs):

        self.stdscr = stdscr
        self.reddit = reddit
        self.content = content
        self.nav = Navigator(self.content.get, **kwargs)

        self._header_window = None
        self._content_window = None
        self._subwindows = None

    def refresh_content(self):
        raise NotImplementedError

    @staticmethod
    def draw_item(window, data, inverted):
        raise NotImplementedError

    @BaseController.register('q')
    def exit(self):
        sys.exit()

    @BaseController.register('?')
    def help(self):
        show_help(self._content_window)

    @BaseController.register(curses.KEY_UP, 'k')
    def move_cursor_up(self):
        self._move_cursor(-1)
        self.clear_input_queue()

    @BaseController.register(curses.KEY_DOWN, 'j')
    def move_cursor_down(self):
        self._move_cursor(1)
        self.clear_input_queue()

    @BaseController.register('n', curses.KEY_NPAGE)
    def move_page_down(self):
        self._move_page(1)
        self.clear_input_queue()

    @BaseController.register('m', curses.KEY_PPAGE)
    def move_page_up(self):
        self._move_page(-1)
        self.clear_input_queue()

    @BaseController.register('a')
    def upvote(self):
        data = self.content.get(self.nav.absolute_index)
        try:
            if 'likes' not in data:
                pass
            elif data['likes']:
                data['object'].clear_vote()
                data['likes'] = None
            else:
                data['object'].upvote()
                data['likes'] = True
        except praw.errors.LoginOrScopeRequired:
            show_notification(self.stdscr, ['Not logged in'])

    @BaseController.register('z')
    def downvote(self):
        data = self.content.get(self.nav.absolute_index)
        try:
            if 'likes' not in data:
                pass
            elif data['likes'] or data['likes'] is None:
                data['object'].downvote()
                data['likes'] = False
            else:
                data['object'].clear_vote()
                data['likes'] = None

        except praw.errors.LoginOrScopeRequired:
            show_notification(self.stdscr, ['Not logged in'])

    @BaseController.register('u')
    def login(self):
        """
        Prompt to log into the user's account, or log out of the current
        account.
        """

        if self.reddit.is_logged_in():
            self.logout()
            return

        username = prompt_input(self.stdscr, 'Enter username:')
        password = prompt_input(self.stdscr, 'Enter password:', hide=True)
        if not username or not password:
            curses.flash()
            return

        try:
            with self.loader(message='Logging in'):
                self.reddit.login(username, password)
        except praw.errors.InvalidUserPass:
            show_notification(self.stdscr, ['Invalid user/pass'])
        else:
            show_notification(self.stdscr, ['Welcome {}'.format(username)])

    @BaseController.register('d')
    def delete(self):
        """
        Delete a submission or comment.
        """

        if not self.reddit.is_logged_in():
            show_notification(self.stdscr, ['Not logged in'])
            return

        data = self.content.get(self.nav.absolute_index)
        if data.get('author') != self.reddit.user.name:
            curses.flash()
            return

        prompt = 'Are you sure you want to delete this? (y/n):'
        char = prompt_input(self.stdscr, prompt)
        if char != 'y':
            show_notification(self.stdscr, ['Aborted'])
            return

        with self.safe_call as s:
            with self.loader(message='Deleting', delay=0):
                data['object'].delete()
                time.sleep(2.0)
            s.catch = False
            self.refresh_content()

    @BaseController.register('e')
    def edit(self):
        """
        Edit a submission or comment.
        """

        if not self.reddit.is_logged_in():
            show_notification(self.stdscr, ['Not logged in'])
            return

        data = self.content.get(self.nav.absolute_index)
        if data.get('author') != self.reddit.user.name:
            curses.flash()
            return

        if data['type'] == 'Submission':
            subreddit = self.reddit.get_subreddit(self.content.name)
            content = data['text']
            info = SUBMISSION_FILE.format(content=content, name=subreddit)
        elif data['type'] == 'Comment':
            content = data['body']
            info = COMMENT_EDIT_FILE.format(content=content)
        else:
            curses.flash()
            return

        text = open_editor(info)
        if text == content:
            show_notification(self.stdscr, ['Aborted'])
            return

        with self.safe_call as s:
            with self.loader(message='Editing', delay=0):
                data['object'].edit(text)
                time.sleep(2.0)
            s.catch = False
            self.refresh_content()

    @BaseController.register('i')
    def get_inbox(self):
        """
        Checks the inbox for unread messages and displays a notification.
        """
        inbox = len(list(self.reddit.get_unread(limit=1)))
        try:
            if inbox > 0:
                show_notification(self.stdscr, ['New Messages'])
            elif inbox == 0:
                show_notification(self.stdscr, ['No New Messages'])
        except praw.errors.LoginOrScopeRequired:
            show_notification(self.stdscr, ['Not Logged In'])

    def clear_input_queue(self):
        """
        Clear excessive input caused by the scroll wheel or holding down a key
        """

        self.stdscr.nodelay(1)
        while self.stdscr.getch() != -1:
            continue
        self.stdscr.nodelay(0)

    def logout(self):
        """
        Prompt to log out of the user's account.
        """

        ch = prompt_input(self.stdscr, "Log out? (y/n):")
        if ch == 'y':
            self.reddit.clear_authentication()
            show_notification(self.stdscr, ['Logged out'])
        elif ch != 'n':
            curses.flash()

    @property
    def safe_call(self):
        """
        Wrap praw calls with extended error handling.
        If a PRAW related error occurs inside of this context manager, a
        notification will be displayed on the screen instead of the entire
        application shutting down. This function will return a callback that
        can be used to check the status of the call.

        Usage:
            #>>> with self.safe_call as s:
            #>>>     self.reddit.submit(...)
            #>>>     s.catch = False
            #>>>     on_success()
        """
        return SafeCaller(self.stdscr)

    def draw(self):

        n_rows, n_cols = self.stdscr.getmaxyx()
        if n_rows < self.MIN_HEIGHT or n_cols < self.MIN_WIDTH:
            return

        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        self._header_window = self.stdscr.derwin(1, n_cols, 0, 0)
        self._content_window = self.stdscr.derwin(n_rows - 1, n_cols, 1, 0)

        self.stdscr.erase()
        self._draw_header()
        self._draw_content()
        self._add_cursor()

    def _draw_header(self):

        n_rows, n_cols = self._header_window.getmaxyx()

        self._header_window.erase()
        attr = curses.A_REVERSE | curses.A_BOLD | Color.CYAN
        self._header_window.bkgd(' ', attr)

        sub_name = self.content.name.replace('/r/front', 'Front Page ')
        add_line(self._header_window, sub_name, 0, 0)

        if self.reddit.user is not None:
            username = self.reddit.user.name
            s_col = (n_cols - textual_width(username) - 1)
            # Only print username if it fits in the empty space on the right
            if (s_col - 1) >= textual_width(sub_name):
                add_line(self._header_window, username, 0, s_col)

        self._header_window.refresh()

    def _draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """

        n_rows, n_cols = self._content_window.getmaxyx()
        self._content_window.erase()
        self._subwindows = []

        page_index, cursor_index, inverted = self.nav.position
        step = self.nav.step

        # If not inverted, align the first submission with the top and draw
        # downwards. If inverted, align the first submission with the bottom
        # and draw upwards.
        current_row = (n_rows - 1) if inverted else 0
        available_rows = (n_rows - 1) if inverted else n_rows
        for data in self.content.iterate(page_index, step, n_cols - 2):
            window_rows = min(available_rows, data['n_rows'])
            window_cols = n_cols - data['offset']
            start = current_row - window_rows if inverted else current_row
            subwindow = self._content_window.derwin(
                window_rows, window_cols, start, data['offset'])
            attr = self.draw_item(subwindow, data, inverted)
            self._subwindows.append((subwindow, attr))
            available_rows -= (window_rows + 1)  # Add one for the blank line
            current_row += step * (window_rows + 1)
            if available_rows <= 0:
                break
        else:
            # If the page is not full we need to make sure that it is NOT
            # inverted. Unfortunately, this currently means drawing the whole
            # page over again. Could not think of a better way to pre-determine
            # if the content will fill up the page, given that it is dependent
            # on the size of the terminal.
            if self.nav.inverted:
                self.nav.flip((len(self._subwindows) - 1))
                self._draw_content()

        self._content_window.refresh()

    def _add_cursor(self):
        self._edit_cursor(curses.A_REVERSE)

    def _remove_cursor(self):
        self._edit_cursor(curses.A_NORMAL)

    def _move_cursor(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            curses.flash()

        # Note: ACS_VLINE doesn't like changing the attribute, so always redraw.
        self._draw_content()
        self._add_cursor()

    def _move_page(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move_page(direction, len(self._subwindows)-1)
        if not valid:
            curses.flash()

        # Note: ACS_VLINE doesn't like changing the attribute, so always redraw.
        self._draw_content()
        self._add_cursor()

    def _edit_cursor(self, attribute=None):

        # Don't allow the cursor to go below page index 0
        if self.nav.absolute_index < 0:
            return

        # Don't allow the cursor to go over the number of subwindows
        # This could happen if the window is resized and the cursor index is
        # pushed out of bounds
        if self.nav.cursor_index >= len(self._subwindows):
            self.nav.cursor_index = len(self._subwindows)-1

        window, attr = self._subwindows[self.nav.cursor_index]
        if attr is not None:
            attribute |= attr

        n_rows, _ = window.getmaxyx()
        for row in range(n_rows):
            window.chgat(row, 0, 1, attribute)

        window.refresh()

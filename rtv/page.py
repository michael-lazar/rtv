import curses

import praw.errors

from .helpers import clean
from .curses_helpers import Color, show_notification

__all__ = ['Navigator']

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

        forward = ((direction*self.step) > 0)

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
                    # We have reached the beginning of the page - move the index
                    redraw = True
                else:
                    self.page_index += self.step
                    valid = False # Revert

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

    def move_cursor_up(self):
        self._move_cursor(-1)

    def move_cursor_down(self):
        self._move_cursor(1)

    def clear_input_queue(self):
        "Clear excessive input caused by the scroll wheel or holding down a key"
        self.stdscr.nodelay(1)
        while self.stdscr.getch() != -1:
            continue
        self.stdscr.nodelay(0)

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
            show_notification(self.stdscr, ['Login to vote'])

    def downvote(self):

        data = self.content.get(self.nav.absolute_index)
        try:
            if 'likes' not in data:
                pass
            if data['likes'] is False:
                data['object'].clear_vote()
                data['likes'] = None
            else:
                data['object'].downvote()
                data['likes'] = False
        except praw.errors.LoginOrScopeRequired:
            show_notification(self.stdscr, ['Login to vote'])

    def draw(self):

        n_rows, n_cols = self.stdscr.getmaxyx()
        if n_rows < self.MIN_HEIGHT or n_cols < self.MIN_WIDTH:
            return

        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        self._header_window = self.stdscr.derwin(1, n_cols, 0, 0)
        self._content_window = self.stdscr.derwin(n_rows-1, n_cols, 1, 0)

        self.stdscr.erase()
        self._draw_header()
        self._draw_content()
        self._add_cursor()

    @staticmethod
    def draw_item(window, data, inverted):
        raise NotImplementedError

    def _draw_header(self):

        n_rows, n_cols = self._header_window.getmaxyx()

        self._header_window.erase()
        attr = curses.A_REVERSE | curses.A_BOLD | Color.CYAN
        self._header_window.bkgd(' ', attr)

        sub_name = self.content.name.replace('/r/front', 'Front Page ')
        self._header_window.addnstr(0, 0, clean(sub_name), n_cols-1)

        if self.reddit.user is not None:
            username = self.reddit.user.name
            s_col = (n_cols - len(username) - 1)
            # Only print the username if it fits in the empty space on the right
            if (s_col - 1) >= len(sub_name):
                n = (n_cols - s_col - 1)
                self._header_window.addnstr(0, s_col, clean(username), n)

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
        for data in self.content.iterate(page_index, step, n_cols-2):
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
        if not valid: curses.flash()

        # Note: ACS_VLINE doesn't like changing the attribute, so always redraw.
        # if redraw: self._draw_content()
        self._draw_content()
        self._add_cursor()

    def _edit_cursor(self, attribute=None):

        # Don't allow the cursor to go below page index 0
        if self.nav.absolute_index < 0:
            return

        window, attr = self._subwindows[self.nav.cursor_index]
        if attr is not None:
            attribute |= attr

        n_rows, _ = window.getmaxyx()
        for row in range(n_rows):
            window.chgat(row, 0, 1, attribute)

        window.refresh()

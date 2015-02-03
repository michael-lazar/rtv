import curses

from utils import Color

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

        # TODO: add variable movement
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
                if self.cursor_index >= n_windows - 1:
                    # We have reached the end of the page - flip the orientation
                    self.page_index += (self.step * self.cursor_index)
                    self.cursor_index = 0
                    self.inverted = not self.inverted
                    redraw = True
        else:
            if self.cursor_index > 0:
                self.cursor_index -= 1
            else:
                if self._is_valid(self.page_index - self.step):
                    # We have reached the beginning of the page - move the index
                    self.page_index -= self.step
                    redraw = True
                else:
                    valid = False

        return valid, redraw

    def _is_valid(self, page_index):
        "Check if a page index will cause entries to fall outside valid range"

        try:
            self._page_cb(page_index)
            self._page_cb(page_index + self.step * self.cursor_index)
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

    def __init__(self, stdscr, content, **kwargs):

        self.stdscr = stdscr
        self.content = content
        self.nav = Navigator(self.content.get, **kwargs)

        self._header_window = None
        self._content_window = None
        self._subwindows = None

    def move_cursor_up(self):
        self._move_cursor(-1)

    def move_cursor_down(self):
        self._move_cursor(1)

    def add_cursor(self):
        self._edit_cursor(curses.A_REVERSE)

    def remove_cursor(self):
        self._edit_cursor(curses.A_NORMAL)

    def clear_input_queue(self):
        "Clear excessive input caused by the scroll wheel or holding down a key"
        self.stdscr.nodelay(1)
        while self.stdscr.getch() != -1:
            continue
        self.stdscr.nodelay(0)

    def draw(self):

        n_rows, n_cols = self.stdscr.getmaxyx()
        if n_rows < self.MIN_HEIGHT or n_cols < self.MIN_WIDTH:
            return

        self._header_window = self.stdscr.derwin(1, n_cols, 0, 0)
        self._content_window = self.stdscr.derwin(1, 0)

        self._draw_header()
        self._draw_content()
        self.add_cursor()

    def draw_item(self, window, data, inverted):
        raise NotImplementedError

    def _draw_header(self):

        n_rows, n_cols = self._header_window.getmaxyx()

        self._header_window.erase()
        attr = curses.A_REVERSE | curses.A_BOLD | Color.RED
        self._header_window.addnstr(0, 0, self.content.name, n_cols-1, attr)
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
        current_row = n_rows if inverted else 0
        available_rows = n_rows
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

        self._content_window.refresh()

    def _move_cursor(self, direction):

        self.remove_cursor()

        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            curses.flash()

        # If we don't redraw, ACS_VLINE gets screwed up when changing the
        # attr back to normal. There may be a way around this.
        if True: #if redraw
            self._draw_content()

        self.add_cursor()

    def _edit_cursor(self, attribute=None):

        # Don't allow the cursor to go below page index 0
        if self.nav.absolute_index < 0:
            return

        # TODO: attach attr to data[attr] or something
        window, attr = self._subwindows[self.nav.cursor_index]
        if attr is not None:
            attribute |= attr

        n_rows, _ = window.getmaxyx()
        for row in xrange(n_rows):
            window.chgat(row, 0, 1, attribute)

        window.refresh()
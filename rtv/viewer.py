import curses

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
            self.cursor_index += 1
            if self.cursor_index >= n_windows - 1:
                self.page_index += (self.step * self.cursor_index)
                self.cursor_index = 0
                self.inverted = not self.inverted
                redraw = True
        else:
            if self.cursor_index > 0:
                self.cursor_index -= 1
            else:
                if self._is_valid(self.page_index - self.step):
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


class BaseViewer(object):
    """
    Base terminal viewer incorperates a cursor to navigate content
    """

    def __init__(self, stdscr, content, **kwargs):

        self.stdscr = stdscr
        self.content = content

        self.nav = Navigator(self.content.get, **kwargs)

        self._subwindows = None
        self.add_loading()

    def draw(self):
        raise NotImplementedError

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

    def add_loading(self):
        "Draw a `loading` popup dialog in the center of the screen"

        message = 'Loading...'

        n_rows, n_cols = self.stdscr.getmaxyx()
        win_rows, win_cols = 3, len(message)+2
        start_row = (n_rows - win_rows) / 2
        start_col = (n_cols - win_cols) / 2
        window = self.stdscr.derwin(win_rows, win_cols, start_row, start_col)
        window.border()
        window.addstr(1, 1, message)
        window.refresh()

    def draw_header(self):

        n_rows, n_cols = self._header_window.getmaxyx()

        self._header_window.erase()
        self._header_window.addnstr(0, 0, self.content.display_name, n_cols-1)

    def draw_content(self):
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
            self.draw_item(subwindow, data, inverted)
            self._subwindows.append(subwindow)
            available_rows -= (window_rows + 1)  # Add one for the blank line
            current_row += step * (window_rows + 1)
            if available_rows <= 0:
                break

        self._content_window.refresh()

    def draw_item(self, window, data, inverted):
        raise NotImplementedError

    def _move_cursor(self, direction):

        self.remove_cursor()

        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            curses.flash()

        # If we don't redraw, ACS_VLINE gets screwed up when changing the
        # attr back to normal. There may be a way around this.
        if True: #if redraw
            self.draw_content()

        self.add_cursor()

    def _edit_cursor(self, attribute):

        # Don't alow the cursor to go below page index 0
        if self.nav.absolute_index == -1:
            window = self._subwindows[self.nav.cursor_index + 1]
        else:
            window = self._subwindows[self.nav.cursor_index]

        n_rows, _ = window.getmaxyx()
        for row in xrange(n_rows):
            window.chgat(row, 0, 1, attribute)

        window.refresh()
import curses

class Navigator(object):
    """
    Handles cursor movement and screen paging.
    """

    def __init__(
            self,
            valid_page_cb,
            page_index=0,
            cursor_index=0,
            inverted=False):

        self._page_cb = valid_page_cb

        self.page_index = page_index
        self.cursor_index = cursor_index
        self.inverted = inverted

    @property
    def step(self):
        return 1 if not self.inverted else -1

    @property
    def position(self):
        return (self.page_index, self.cursor_index, self.inverted)

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
    Base terminal viewer incorperating a cursor to navigate content
    """

    def __init__(self, content):

        self.content = content
        self.nav = Navigator(self.content.get)
        self._subwindows = None

    def draw_content(self):
        raise NotImplementedError

    def move_cursor_up(self):
        self._move_cursor(-1)

    def move_cursor_down(self):
        self._move_cursor(1)

    def add_cursor(self):
        curses.curs_set(2)
        self._edit_cursor(curses.A_REVERSE)

    def remove_cursor(self):
        curses.curs_set(0)
        self._edit_cursor(curses.A_NORMAL)

    def _move_cursor(self, direction):

        self.remove_cursor()

        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            curses.flash()
        if redraw:
            self.draw_content()

        self.add_cursor()

    def _edit_cursor(self, attribute):

        window = self._subwindows[self.nav.cursor_index]

        n_rows, _ = window.getmaxyx()
        for row in xrange(n_rows):
            window.chgat(row, 0, 1, attribute)
        window.move(0, 0)

        window.refresh()
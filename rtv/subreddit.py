import praw
import textwrap
import curses

from content_generators import SubredditGenerator
from utils import curses_session

class SubredditViewer(object):

    def __init__(self, stdscr, subreddit_generator):

        self.stdscr = stdscr
        self.gen = subreddit_generator

        self._cursor_index = 0
        self._page_index = 0
        self._rows = None
        self._cols = None
        self._title_window = None
        self._content_window = None
        self._sub_windows = []
        self._direction = True
        self._window_is_partial = None

        self.draw()

    def loop(self):

        while True:
            cmd = self.stdscr.getch()

            # Move cursor up one submission
            if cmd == curses.KEY_UP:
                if self._direction:
                    self.move_cursor_backward()
                else:
                    self.move_cursor_forward()

            # Move cursor down one submission
            elif cmd == curses.KEY_DOWN:
                if self._direction:
                    self.move_cursor_forward()
                else:
                    self.move_cursor_backward()

            # View submission
            elif cmd in (curses.KEY_RIGHT, ord(' ')):
                pass

            # Enter edit mode to change subreddit
            elif cmd == ord('/'):
                pass

            # Refresh page
            elif cmd in (curses.KEY_F5, ord('r')):
                self.draw()

            # Quit
            elif cmd == ord('q'):
                pass

            else:
                curses.beep()

    def draw(self):

        # Refresh window bounds incase the screen has been resized
        self._rows, self._cols = self.stdscr.getmaxyx()
        self._title_window = self.stdscr.derwin(1, self._cols, 0, 0)
        self._content_window = self.stdscr.derwin(1, 0)

        self.draw_header()
        self.draw_content()
        self.draw_cursor()

    def move_cursor_forward(self):

        self.remove_cursor()

        last_index = len(self._sub_windows) - 1

        self._cursor_index += 1
        if self._cursor_index == last_index:

            if self._direction:
                self._page_index = self._page_index + self._cursor_index
                self._cursor_index = 0
                self._direction = False
            else:
                self._page_index = self._page_index - self._cursor_index
                self._cursor_index = 0
                self._direction = True
            self.draw_content()

        self.draw_cursor()

    def move_cursor_backward(self):

        self.remove_cursor()

        last_index = len(self._sub_windows) - 1

        self._cursor_index -= 1
        if self._cursor_index < 0:

            if self._direction:
                self._page_index -= 1
                self._cursor_index = 0
            else:
                self._page_index += 1
                self._cursor_index = 0
            self.draw_content()

        self.draw_cursor()

    def draw_cursor(self):

        window = self._sub_windows[self._cursor_index]
        rows, _ = window.getmaxyx()
        for row in xrange(rows):
            window.chgat(row, 0, 1, curses.A_REVERSE)
        window.refresh()

    def remove_cursor(self):

        window = self._sub_windows[self._cursor_index]
        rows, _ = window.getmaxyx()
        for row in xrange(rows):
            window.chgat(row, 0, 1, curses.A_NORMAL)
        window.refresh()

    def draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """

        rows, cols = self._content_window.getmaxyx()
        self._content_window.erase()
        self._sub_windows = []

        if self._direction:
            row = 0
            for data in self.gen.iterate(self._page_index, 1, cols-1):
                available_rows = (rows - row)
                n_rows = min(available_rows, data['n_rows'])
                window = self._content_window.derwin(n_rows, cols, row, 0)
                self.draw_submission(window, data, self._direction)
                self._sub_windows.append(window)
                row += (n_rows + 1)
                if row >= rows:
                    break
        else:
            row = rows
            for data in self.gen.iterate(self._page_index, -1, cols-1):
                available_rows = row
                n_rows = min(available_rows, data['n_rows'])
                window = self._content_window.derwin(n_rows, cols, row-n_rows, 0)
                self.draw_submission(window, data, self._direction)
                self._sub_windows.append(window)
                row -= (n_rows + 1)
                if row < 0:
                    break

        self._window_is_partial = (available_rows < data['n_rows'])
        self._content_window.refresh()

    def draw_header(self):

        self._title_window.erase()
        self._title_window.addnstr(0, 0, self.gen.display_name, self._cols)
        self._title_window.refresh()

    @staticmethod
    def draw_submission(win, data, direction):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if direction else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                win.addstr(row, 1, text)

        row = n_title + offset
        if row in valid_rows:
            win.addnstr(row, 1, '{url}'.format(**data), n_cols-1)

        row = n_title + offset + 1
        if row in valid_rows:
            win.addnstr(row, 1, '{created} {comments} {score}'.format(**data), n_cols-1)

        row = n_title + offset + 2
        if row in valid_rows:
            win.addnstr(row, 1, '{author} {subreddit}'.format(**data), n_cols-1)


def main():

    with curses_session() as stdscr:
        r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
        generator = SubredditGenerator(r)
        viewer = SubredditViewer(stdscr, generator)
        viewer.loop()

if __name__ == '__main__':

    main()

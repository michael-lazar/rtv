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

        self.draw()

    def loop(self):

        while True:
            cmd = self.stdscr.getch()

            # Move cursor up one submission
            if cmd == curses.KEY_UP:
                self.move_cursor(-1)

            # Move cursor down one submission
            elif cmd == curses.KEY_DOWN:
                self.move_cursor(1)

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

    def move_cursor(self, delta):

        new_index = self._cursor_index + delta
        if new_index < 0:
            curses.flash()
            return



        self.remove_cursor()
        self._cursor_index += delta
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

        row = 0
        for data in self.gen.iterate(self._page_index, cols-1):
            n_rows = min(rows-row, data['n_rows'])
            window = self._content_window.derwin(n_rows, cols, row, 0)
            self.draw_submission(window, data)
            self._sub_windows.append(window)
            row += n_rows + 1
            if row >= rows:
                break

        self._content_window.refresh()

    def draw_header(self):

        self._title_window.erase()
        self._title_window.addnstr(0, 0, self.gen.display_name, self._cols)
        self._title_window.refresh()

    @staticmethod
    def draw_submission(win, data, top_down=True):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if top_down else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                win.addstr(row, 1, text)

        row = n_title
        if row in valid_rows:
            win.addnstr(row, 1, '{url}'.format(**data), n_cols)

        row = n_title + 1
        if row in valid_rows:
            win.addnstr(row, 1, '{created} {comments} {score}'.format(**data), n_cols)

        row = n_title + 2
        if row in valid_rows:
            win.addnstr(row, 1, '{author} {subreddit}'.format(**data), n_cols)

        # DEBUG
        win.refresh()


def main():

    with curses_session() as stdscr:
        r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
        generator = SubredditGenerator(r)
        viewer = SubredditViewer(stdscr, generator)
        viewer.loop()

if __name__ == '__main__':

    main()

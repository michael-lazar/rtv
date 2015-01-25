import praw
import textwrap
import curses

from content_generators import SubredditGenerator
from utils import curses_session
from viewer import BaseViewer

class SubredditViewer(BaseViewer):

    def __init__(self, stdscr, subreddit_content):

        self.stdscr = stdscr

        self._n_rows = None
        self._n_cols = None
        self._title_window = None
        self._content_window = None

        super(SubredditViewer, self).__init__(subreddit_content)
        self.draw()

    def loop(self):
        while True:
            cmd = self.stdscr.getch()

            if cmd == curses.KEY_UP:
                self.move_cursor_up()

            elif cmd == curses.KEY_DOWN:
                self.move_cursor_down()

            # View submission
            elif cmd in (curses.KEY_RIGHT, ord(' ')):
                pass

            # Enter edit mode to change subreddit
            elif cmd == ord('/'):
                pass

            # Refresh page
            elif cmd in (curses.KEY_F5, ord('r')):
                self.content.reset()
                self.stdscr.clear()
                self.draw()

            # Quit
            elif cmd == ord('q'):
                break

            else:
                curses.beep()

    def draw(self):

        # Refresh window bounds incase the screen has been resized
        self._n_rows, self._n_cols = self.stdscr.getmaxyx()
        self._title_window = self.stdscr.derwin(1, self._n_cols, 0, 0)
        self._content_window = self.stdscr.derwin(1, 0)

        self.draw_header()
        self.draw_content()
        self.add_cursor()

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
        for data in self.content.iterate(page_index, step, n_cols-1):
            window_rows = min(available_rows, data['n_rows'])
            start = current_row - window_rows if inverted else current_row
            window = self._content_window.derwin(window_rows, n_cols, start, 0)
            self.draw_submission(window, data, inverted)
            self._subwindows.append(window)
            available_rows -= (window_rows + 1)  # Add one for the blank line
            current_row += step * (window_rows + 1)
            if available_rows <= 0:
                break

        self._content_window.refresh()

    def draw_header(self):

        sub_name = self.content.display_name
        self._title_window.erase()
        self._title_window.addnstr(0, 0, sub_name, self._n_cols)
        self._title_window.refresh()

    @staticmethod
    def draw_submission(win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

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

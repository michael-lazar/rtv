import praw
import textwrap
import curses
import sys

from content_generators import SubredditContent, SubmissionContent
from submission_viewer import SubmissionViewer
from viewer import BaseViewer
from utils import curses_session

class SubredditViewer(BaseViewer):

    def loop(self):

        self.draw()
        while True:
            cmd = self.stdscr.getch()

            if cmd == curses.KEY_UP:
                self.move_cursor_up()
                self.clear_input_queue()

            elif cmd == curses.KEY_DOWN:
                self.move_cursor_down()
                self.clear_input_queue()

            # View submission
            elif cmd in (curses.KEY_RIGHT, ord(' ')):
                self.open_submission()
                self.draw()

            # Enter edit mode to change subreddit
            elif cmd == ord('/'):
                pass

            # Refresh page
            elif cmd in (curses.KEY_F5, ord('r')):
                self.refresh_content()

            elif cmd == curses.KEY_RESIZE:
                self.draw()

            # Quit
            elif cmd == ord('q'):
                sys.exit()

            else:
                curses.beep()

    def open_submission(self):
        "Select the current submission to view posts"

        self.add_loading()

        submission = self.content.get(self.nav.absolute_index)['object']
        content = SubmissionContent(submission)
        viewer = SubmissionViewer(self.stdscr, content)
        viewer.loop()

    def draw(self):

        n_rows, n_cols = self.stdscr.getmaxyx()
        self._header_window = self.stdscr.derwin(1, n_cols, 0, 0)
        self._content_window = self.stdscr.derwin(1, 0)

        self.draw_header()
        self.draw_content()
        self.add_cursor()

    @staticmethod
    def draw_item(win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 2  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                win.addstr(row, 1, text)

        row = n_title + offset
        if row in valid_rows:
            win.addnstr(row, 1, '{url}'.format(**data), n_cols)

        row = n_title + offset + 1
        if row in valid_rows:
            win.addnstr(row, 1, '{created} {comments} {score}'.format(**data), n_cols)

        row = n_title + offset + 2
        if row in valid_rows:
            win.addnstr(row, 1, '{author} {subreddit}'.format(**data), n_cols)

def main():

    with curses_session() as stdscr:
        r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
        generator = SubredditContent(r)
        viewer = SubredditViewer(stdscr, generator)
        viewer.loop()

if __name__ == '__main__':

    main()

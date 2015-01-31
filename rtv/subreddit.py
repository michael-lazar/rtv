import praw
import textwrap
import curses
import sys

from page import BasePage
from submission import SubmissionPage
from content import SubmissionContent
from utils import curses_session, text_input

class SubredditPage(BasePage):

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
                self.prompt_subreddit()

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

    def refresh_content(self, subreddit=None):

        self.nav.page_index, self.nav.cursor_index = 0, 0
        self.nav.inverted = False
        self.content.reset(subreddit=subreddit)
        self.stdscr.clear()
        self.draw()

    def prompt_subreddit(self):

        prompt = 'Enter Subreddit: /r/'
        n_rows, n_cols = self.stdscr.getmaxyx()
        self.stdscr.addstr(n_rows-1, 0, prompt)
        self.stdscr.refresh()
        window = self.stdscr.derwin(n_rows-1, len(prompt))

        out = text_input(window)
        if out is None:
            self.draw()
        else:
            self.refresh_content(subreddit=out)

    def open_submission(self):
        "Select the current submission to view posts"

        submission = self.content.get(self.nav.absolute_index)['object']
        content = SubmissionContent(submission, loader=self.content.loader)
        page = SubmissionPage(self.stdscr, content)
        page.loop()

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
import curses
import sys

from content import SubmissionContent
from page import BasePage
from utils import LoadScreen

class SubmissionPage(BasePage):

    def __init__(self, stdscr, reddit, url=None, submission=None):

        self.loader = LoadScreen(stdscr)

        if url is not None:
            content = SubmissionContent.from_url(reddit, url, self.loader)
        elif submission is not None:
            content = SubmissionContent(submission, self.loader)
        else:
            raise ValueError('Must specify url or submission')

        super(SubmissionPage, self).__init__(
            stdscr, content, page_index=-1, cursor_index=1)

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

            # Refresh page
            elif cmd in (curses.KEY_F5, ord('r')):
                self.refresh_content()

            # Show / hide a comment tree
            elif cmd == ord(' '):
                self.toggle_comment()

            elif cmd == curses.KEY_RESIZE:
                self.draw()

            # Go back
            elif cmd in (ord('b'), 27, curses.KEY_LEFT):
                break

            # Quit
            elif cmd == ord('q'):
                sys.exit()

            else:
                curses.beep()

    def toggle_comment(self):

        self.content.toggle(self.nav.absolute_index)
        self.draw()

    def refresh_content(self):

        self.content.reset()
        self.stdscr.clear()
        self.draw()

    def draw_item(self, win, data, inverted=False):

        if data['type'] == 'MoreComments':
            self.draw_more_comments(win, data)

        elif data['type'] == 'HiddenComment':
            self.draw_more_comments(win, data)

        elif data['type'] == 'Comment':
            self.draw_comment(win, data, inverted=inverted)

        else:
            self.draw_submission(win, data)

    @staticmethod
    def draw_comment(win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 2

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        row = offset
        text = '{} {} {}'.format(data['author'], data['score'], data['created'])
        if row in valid_rows:
            win.addnstr(row, 1, text, n_cols)

        n_body = len(data['split_body'])
        for row, text in enumerate(data['split_body'], start=offset+1):
            if row in valid_rows:
                win.addnstr(row, 1, text, n_cols)

        # Vertical line, unfortunately vline() doesn't support custom color so
        # we have to build it one chr at a time.
        for y in xrange(n_rows):
            win.addch(y, 0, curses.ACS_VLINE)

    @staticmethod
    def draw_more_comments(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 2
        win.addnstr(0, 1, data['body'], n_cols)

        for y in xrange(n_rows):
            win.addch(y, 0, curses.ACS_VLINE)

    @staticmethod
    def draw_submission(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 3 # one for each side of the border + one for offset
        # Don't print at all if there is not enough room to fit the whole sub
        if data['n_rows'] > n_rows:
            return

        for row, text in enumerate(data['split_title'], start=1):
            win.addnstr(row, 1, text, n_cols)

        text = '{} {} {}'.format(data['author'], data['created'], data['subreddit'])
        row = len(data['split_title']) + 1
        win.addnstr(row, 1, text, n_cols)

        row = len(data['split_title']) + 2
        win.addnstr(row, 1, data['url'], n_cols)

        offset = len(data['split_title']) + 3
        for row, text in enumerate(data['split_text'], start=offset):
            win.addnstr(row, 1, text, n_cols)

        text = '{} {}'.format(data['score'], data['comments'])
        row = len(data['split_title']) + len(data['split_text']) + 3
        win.addnstr(row, 1, text, n_cols)

        win.border()
import curses
import sys
import webbrowser

import six

from .content import SubmissionContent
from .page import BasePage
from .utils import LoadScreen, Color, ESCAPE

class SubmissionPage(BasePage):

    def __init__(self, stdscr, reddit, url=None, submission=None):

        self.loader = LoadScreen(stdscr)

        if url is not None:
            content = SubmissionContent.from_url(reddit, url, self.loader)
        elif submission is not None:
            content = SubmissionContent(submission, self.loader)
        else:
            raise ValueError('Must specify url or submission')

        super(SubmissionPage, self).__init__(stdscr, content, page_index=-1)

    def loop(self):

        self.draw()
        while True:
            cmd = self.stdscr.getch()

            if cmd in (curses.KEY_UP, ord('k')):
                self.move_cursor_up()
                self.clear_input_queue()

            elif cmd in (curses.KEY_DOWN, ord('j')):
                self.move_cursor_down()
                self.clear_input_queue()

            elif cmd in (curses.KEY_F5, ord('r')):
                self.refresh_content()
                self.draw()

            elif cmd in (curses.KEY_RIGHT, curses.KEY_ENTER, ord('l')):
                self.toggle_comment()
                self.draw()

            elif cmd == ord('o'):
                self.open_link()

            elif cmd == curses.KEY_RESIZE:
                self.draw()

            elif cmd in (ESCAPE, curses.KEY_LEFT, ord('h')):
                break

            elif cmd == ord('q'):
                sys.exit()

            else:
                curses.beep()

    def toggle_comment(self):

        self.content.toggle(self.nav.absolute_index)

    def refresh_content(self):

        self.content.reset()
        self.nav.page_index, self.nav.cursor_index = -1, 0
        self.nav.inverted = False

    def open_link(self):

        # Always open the page for the submission
        # May want to expand at some point to open comment permalinks
        url = self.content.get(-1)['permalink']
        webbrowser.open_new_tab(url)

    def draw_item(self, win, data, inverted=False):

        if data['type'] == 'MoreComments':
            return self.draw_more_comments(win, data)

        elif data['type'] == 'HiddenComment':
            return self.draw_more_comments(win, data)

        elif data['type'] == 'Comment':
            return self.draw_comment(win, data, inverted=inverted)

        else:
            return self.draw_submission(win, data)

    @staticmethod
    def draw_comment(win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        row = offset
        if row in valid_rows:
            text = '{author}'.format(**data)
            attr = curses.A_BOLD
            attr |= (Color.BLUE if not data['is_author'] else Color.GREEN)
            win.addnstr(row, 1, text, n_cols-1, attr)
            text = ' {score} {created}'.format(**data)
            win.addnstr(text, n_cols - win.getyx()[1])

        n_body = len(data['split_body'])
        for row, text in enumerate(data['split_body'], start=offset+1):
            if row in valid_rows:
                win.addnstr(row, 1, text, n_cols-1)

        # Vertical line, unfortunately vline() doesn't support custom color so
        # we have to build it one chr at a time.
        attr = Color.get_level(data['level'])
        for y in range(n_rows):

            x = 0

            # Nobody pays attention to curses ;(
            # http://bugs.python.org/issue21088
            if (sys.version_info.major,
                sys.version_info.minor, 
                sys.version_info.micro) == (3, 4, 0):
                x, y = y, x
            
            win.addch(y, x, curses.ACS_VLINE, attr)

        return attr | curses.ACS_VLINE

    @staticmethod
    def draw_more_comments(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1
        text = '{body}'.format(**data)
        win.addnstr(0, 1, text, n_cols-1)
        text = ' [{count}]'.format(**data)
        win.addnstr(text, n_cols - win.getyx()[1], curses.A_BOLD)

        attr = Color.get_level(data['level'])
        for y in range(n_rows):
            win.addch(y, 0, curses.ACS_VLINE, attr)

        return attr | curses.ACS_VLINE

    @staticmethod
    def draw_submission(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 3 # one for each side of the border + one for offset

        # Don't print at all if there is not enough room to fit the whole sub
        if data['n_rows'] > n_rows:
            win.addnstr(0, 0, '(Not enough space to display)', n_cols)
            return

        for row, text in enumerate(data['split_title'], start=1):
            win.addnstr(row, 1, text, n_cols, curses.A_BOLD)

        row = len(data['split_title']) + 1
        attr = curses.A_BOLD | Color.GREEN
        text = '{author}'.format(**data)
        win.addnstr(row, 1, text, n_cols, attr)
        text = ' {created} {subreddit}'.format(**data)
        win.addnstr(text, n_cols - win.getyx()[1])

        row = len(data['split_title']) + 2
        attr = curses.A_UNDERLINE | Color.BLUE
        text = '{url}'.format(**data)
        win.addnstr(row, 1, text, n_cols, attr)

        offset = len(data['split_title']) + 3
        for row, text in enumerate(data['split_text'], start=offset):
            win.addnstr(row, 1, text, n_cols)

        row = len(data['split_title']) + len(data['split_text']) + 3
        text = '{score} {comments}'.format(**data)
        win.addnstr(row, 1, text, n_cols, curses.A_BOLD)

        win.border()

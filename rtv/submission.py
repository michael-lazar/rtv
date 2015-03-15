import curses
import sys
import time
import praw.errors

from .content import SubmissionContent
from .page import BasePage
from .utils import (LoadScreen, Color, Symbol, display_help, open_browser,
                    text_input, display_message)

class SubmissionPage(BasePage):

    def __init__(self, stdscr, reddit, url=None, submission=None):

        self.loader = LoadScreen(stdscr)

        if url is not None:
            content = SubmissionContent.from_url(reddit, url, self.loader)
        elif submission is not None:
            content = SubmissionContent(submission, self.loader)
        else:
            raise ValueError('Must specify url or submission')

        super(SubmissionPage, self).__init__(stdscr, reddit, content, page_index=-1)

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

            elif cmd in (curses.KEY_RIGHT, curses.KEY_ENTER, ord('l')):
                self.toggle_comment()
                self.draw()

            elif cmd in (curses.KEY_LEFT, ord('h')):
                break

            elif cmd == ord('o'):
                self.open_link()
                self.draw()

            elif cmd in (curses.KEY_F5, ord('r')):
                self.refresh_content()
                self.draw()

            elif cmd == ord('c'):
                self.add_comment()
                self.draw()
                
            elif cmd == ord('?'):
                display_help(self.stdscr)
                self.draw()

            elif cmd == ord('a'):
                self.upvote()
                self.draw()

            elif cmd == ord('z'):
                self.downvote()
                self.draw()

            elif cmd == ord('q'):
                sys.exit()

            elif cmd == curses.KEY_RESIZE:
                self.draw()

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
        open_browser(url)

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

            text = Symbol.clean('{author} '.format(**data))
            attr = curses.A_BOLD
            attr |= (Color.BLUE if not data['is_author'] else Color.GREEN)
            win.addnstr(row, 1, text, n_cols-1, attr)

            if data['flair']:
                text = Symbol.clean('{flair} '.format(**data))
                attr = curses.A_BOLD | Color.YELLOW
                win.addnstr(text, n_cols-win.getyx()[1], attr)

            if data['likes'] is None:
                text, attr = Symbol.BULLET, curses.A_BOLD
            elif data['likes']:
                text, attr = Symbol.UARROW, (curses.A_BOLD | Color.GREEN)
            else:
                text, attr = Symbol.DARROW, (curses.A_BOLD | Color.RED)
            win.addnstr(text, n_cols-win.getyx()[1], attr)

            text = Symbol.clean(' {score} {created}'.format(**data))
            win.addnstr(text, n_cols-win.getyx()[1])

        n_body = len(data['split_body'])
        for row, text in enumerate(data['split_body'], start=offset+1):
            if row in valid_rows:
                text = Symbol.clean(text)
                win.addnstr(row, 1, text, n_cols-1)

        # Unfortunately vline() doesn't support custom color so we have to
        # build it one segment at a time.
        attr = Color.get_level(data['level'])
        for y in range(n_rows):
            x = 0
            # http://bugs.python.org/issue21088
            if (sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro) == (3, 4, 0):
                x, y = y, x

            win.addch(y, x, curses.ACS_VLINE, attr)

        return (attr | curses.ACS_VLINE)

    @staticmethod
    def draw_more_comments(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1

        text = Symbol.clean('{body}'.format(**data))
        win.addnstr(0, 1, text, n_cols-1)
        text = Symbol.clean(' [{count}]'.format(**data))
        win.addnstr(text, n_cols-win.getyx()[1], curses.A_BOLD)

        # Unfortunately vline() doesn't support custom color so we have to
        # build it one segment at a time.
        attr = Color.get_level(data['level'])
        win.addch(0, 0, curses.ACS_VLINE, attr)

        return (attr | curses.ACS_VLINE)

    @staticmethod
    def draw_submission(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 3 # one for each side of the border + one for offset

        # Don't print at all if there is not enough room to fit the whole sub
        if data['n_rows'] > n_rows:
            win.addnstr(0, 0, '(Not enough space to display)', n_cols)
            return

        for row, text in enumerate(data['split_title'], start=1):
            text = Symbol.clean(text)
            win.addnstr(row, 1, text, n_cols, curses.A_BOLD)

        row = len(data['split_title']) + 1
        attr = curses.A_BOLD | Color.GREEN
        text = Symbol.clean('{author}'.format(**data))
        win.addnstr(row, 1, text, n_cols, attr)
        attr = curses.A_BOLD | Color.YELLOW
        text = Symbol.clean(' {flair}'.format(**data))
        win.addnstr(text, n_cols-win.getyx()[1], attr)
        text = Symbol.clean(' {created} {subreddit}'.format(**data))
        win.addnstr(text, n_cols-win.getyx()[1])

        row = len(data['split_title']) + 2
        attr = curses.A_UNDERLINE | Color.BLUE
        text = Symbol.clean('{url}'.format(**data))
        win.addnstr(row, 1, text, n_cols, attr)

        offset = len(data['split_title']) + 3
        for row, text in enumerate(data['split_text'], start=offset):
            text = Symbol.clean(text)
            win.addnstr(row, 1, text, n_cols)

        row = len(data['split_title']) + len(data['split_text']) + 3
        text = Symbol.clean('{score} {comments}'.format(**data))
        win.addnstr(row, 1, text, n_cols, curses.A_BOLD)

        win.border()

    def add_comment(self):
        """
        Add a comment on the submission if a header is selected.
        Reply to a comment if the comment is selected.
        """

        if not self.reddit.is_logged_in():
            display_message(self.stdscr, ["You are not logged in!"])
            return

        cursor_position = self.nav.absolute_index
        if (self.content.get(cursor_position)['type'] != 'Comment') \
           & (self.content.get(cursor_position)['type'] != 'Submission'):
            display_message(self.stdscr, ['Expand the comments first!'])
            return

        n_rows, n_cols = self.stdscr.getmaxyx()
        box_height = n_rows/2

        attr = curses.A_BOLD | Color.CYAN
        prompt = 'Enter comment: ESC to cancel, Ctrl+g to submit'
        prompt = '-'*((n_cols-len(prompt))/2) + prompt \
                 + '-'*((n_cols-len(prompt)+1)/2)
        self.stdscr.addstr(n_rows-box_height-1, 0, prompt, attr)
        self.stdscr.refresh()

        window = self.stdscr.derwin(box_height, n_cols,
                                    n_rows-box_height, 0)
        window.attrset(attr)

        comment_text = text_input(window, show_cursor=True, insert_mode=False)
        if comment_text is not None:
            try:
                if cursor_position == -1:  # comment on submission
                    self.content._submission.add_comment(comment_text)
                else:  # reply on a selected comment
                    self.content.get(cursor_position)['object']\
                                .reply(comment_text)
            except praw.errors.APIException as e:
                display_message(self.stdscr, [e.message])
            else:
                time.sleep(0.5)
                self.refresh_content()

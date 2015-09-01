import curses
import sys
import time
import logging

from .content import SubmissionContent
from .page import BasePage, Navigator, BaseController
from .helpers import open_browser, open_editor
from .curses_helpers import (Color, LoadScreen, get_arrow, get_gold, add_line,
                             show_notification)
from .docs import COMMENT_FILE

__all__ = ['SubmissionController', 'SubmissionPage']
_logger = logging.getLogger(__name__)


class SubmissionController(BaseController):
    character_map = {}


class SubmissionPage(BasePage):

    def __init__(self, stdscr, reddit, oauth, url=None, submission=None):

        self.controller = SubmissionController(self)
        self.loader = LoadScreen(stdscr)
        self.oauth = oauth
        if url:
            content = SubmissionContent.from_url(reddit, url, self.loader)
        elif submission:
            content = SubmissionContent(submission, self.loader)
        else:
            raise ValueError('Must specify url or submission')

        super(SubmissionPage, self).__init__(stdscr, reddit,
                                             content, oauth, page_index=-1)

    def loop(self):
        "Main control loop"

        self.active = True
        while self.active:
            self.draw()
            cmd = self.stdscr.getch()
            self.controller.trigger(cmd)

    @SubmissionController.register(curses.KEY_RIGHT, 'l', ' ')
    def toggle_comment(self):
        "Toggle the selected comment tree between visible and hidden"

        current_index = self.nav.absolute_index
        self.content.toggle(current_index)
        if self.nav.inverted:
            # Reset the page so that the bottom is at the cursor position.
            # This is a workaround to handle if folding the causes the
            # cursor index to go out of bounds.
            self.nav.page_index, self.nav.cursor_index = current_index, 0

    @SubmissionController.register(curses.KEY_LEFT, 'h')
    def exit_submission(self):
        "Close the submission and return to the subreddit page"

        self.active = False

    @SubmissionController.register(curses.KEY_F5, 'r')
    def refresh_content(self, order=None):
        "Re-download comments reset the page index"

        order = order or self.content.order
        self.content = SubmissionContent.from_url(
            self.reddit, self.content.name, self.loader, order=order)
        self.nav = Navigator(self.content.get, page_index=-1)

    @SubmissionController.register(curses.KEY_ENTER, 10, 'o')
    def open_link(self):
        "Open the current submission page with the webbrowser"

        data = self.content.get(self.nav.absolute_index)
        url = data.get('permalink')
        if url:
            open_browser(url)
        else:
            curses.flash()

    @SubmissionController.register('c')
    def add_comment(self):
        """
        Add a top-level comment if the submission is selected, or reply to the
        selected comment.
        """

        if not self.reddit.is_oauth_session():
            show_notification(self.stdscr, ['Not logged in'])
            return

        data = self.content.get(self.nav.absolute_index)
        if data['type'] == 'Submission':
            content = data['text']
        elif data['type'] == 'Comment':
            content = data['body']
        else:
            curses.flash()
            return

        # Comment out every line of the content
        content = '\n'.join(['# |' + line for line in content.split('\n')])
        comment_info = COMMENT_FILE.format(
            author=data['author'],
            type=data['type'].lower(),
            content=content)

        comment_text = open_editor(comment_info)
        if not comment_text:
            show_notification(self.stdscr, ['Aborted'])
            return

        with self.safe_call as s:
            with self.loader(message='Posting', delay=0):
                if data['type'] == 'Submission':
                    data['object'].add_comment(comment_text)
                else:
                    data['object'].reply(comment_text)
                time.sleep(2.0)
            s.catch = False
            self.refresh_content()

    @SubmissionController.register('d')
    def delete_comment(self):
        "Delete a comment as long as it is not the current submission"

        if self.nav.absolute_index != -1:
            self.delete()
        else:
            curses.flash()

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

        # Handle the case where the window is not large enough to fit the text.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        row = offset
        if row in valid_rows:

            attr = curses.A_BOLD
            attr |= (Color.BLUE if not data['is_author'] else Color.GREEN)
            add_line(win, u'{author} '.format(**data), row, 1, attr)

            if data['flair']:
                attr = curses.A_BOLD | Color.YELLOW
                add_line(win, u'{flair} '.format(**data), attr=attr)

            text, attr = get_arrow(data['likes'])
            add_line(win, text, attr=attr)
            add_line(win, u' {score} {created} '.format(**data))

            if data['gold']:
                text, attr = get_gold()
                add_line(win, text, attr=attr)

        for row, text in enumerate(data['split_body'], start=offset + 1):
            if row in valid_rows:
                add_line(win, text, row, 1)

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

        add_line(win, u'{body}'.format(**data), 0, 1)
        add_line(win, u' [{count}]'.format(**data), attr=curses.A_BOLD)

        attr = Color.get_level(data['level'])
        win.addch(0, 0, curses.ACS_VLINE, attr)

        return (attr | curses.ACS_VLINE)

    @staticmethod
    def draw_submission(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 3  # one for each side of the border + one for offset

        for row, text in enumerate(data['split_title'], start=1):
            add_line(win, text, row, 1, curses.A_BOLD)

        row = len(data['split_title']) + 1
        attr = curses.A_BOLD | Color.GREEN
        add_line(win, u'{author}'.format(**data), row, 1, attr)
        attr = curses.A_BOLD | Color.YELLOW
        if data['flair']:
            add_line(win, u' {flair}'.format(**data), attr=attr)
        add_line(win, u' {created} {subreddit}'.format(**data))

        row = len(data['split_title']) + 2
        attr = curses.A_UNDERLINE | Color.BLUE
        add_line(win, u'{url}'.format(**data), row, 1, attr)
        offset = len(data['split_title']) + 3

        # Cut off text if there is not enough room to display the whole post
        split_text = data['split_text']
        if data['n_rows'] > n_rows:
            cutoff = data['n_rows'] - n_rows + 1
            split_text = split_text[:-cutoff]
            split_text.append('(Not enough space to display)')

        for row, text in enumerate(split_text, start=offset):
            add_line(win, text, row, 1)

        row = len(data['split_title']) + len(split_text) + 3
        add_line(win, u'{score} '.format(**data), row, 1)
        text, attr = get_arrow(data['likes'])
        add_line(win, text, attr=attr)
        add_line(win, u' {comments} '.format(**data))

        if data['gold']:
            text, attr = get_gold()
            add_line(win, text, attr=attr)

        if data['nsfw']:
            text, attr = 'NSFW', (curses.A_BOLD | Color.RED)
            add_line(win, text, attr=attr)

        win.border()

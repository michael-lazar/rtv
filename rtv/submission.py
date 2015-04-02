import curses
import sys
import time

import praw.errors

from .content import SubmissionContent
from .page import BasePage, Navigator, BaseController
from .helpers import clean, open_browser, open_editor
from .curses_helpers import (BULLET, UARROW, DARROW, Color, LoadScreen,
                             show_notification, text_input)
from .docs import COMMENT_FILE, COMMENT_EDIT_FILE

__all__ = ['SubmissionController', 'SubmissionPage']


class SubmissionController(BaseController):
    character_map = {}


class SubmissionPage(BasePage):

    def __init__(self, stdscr, reddit, url=None, submission=None):

        self.controller = SubmissionController(self)
        self.loader = LoadScreen(stdscr)
        if url is not None:
            content = SubmissionContent.from_url(reddit, url, self.loader)
        elif submission is not None:
            content = SubmissionContent(submission, self.loader)
        else:
            raise ValueError('Must specify url or submission')

        super(SubmissionPage, self).__init__(stdscr, reddit, content,
                                             page_index=-1)

    def loop(self):
        self.active = True
        while self.active:
            self.draw()
            cmd = self.stdscr.getch()
            self.controller.trigger(cmd)

    @SubmissionController.register(curses.KEY_RIGHT, 'l')
    def toggle_comment(self):
        current_index = self.nav.absolute_index
        self.content.toggle(current_index)
        if self.nav.inverted:
            # Reset the page so that the bottom is at the cursor position.
            # This is a workaround to handle if folding the causes the
            # cursor index to go out of bounds.
            self.nav.page_index, self.nav.cursor_index = current_index, 0

    @SubmissionController.register(curses.KEY_LEFT, 'h')
    def exit_submission(self):
        self.active = False

    @SubmissionController.register(curses.KEY_F5, 'r')
    def refresh_content(self):
        url = self.content.name
        self.content = SubmissionContent.from_url(
            self.reddit,
            url,
            self.loader)
        self.nav = Navigator(self.content.get, page_index=-1)

    @SubmissionController.register(curses.KEY_ENTER, 10, 'o')
    def open_link(self):
        # Always open the page for the submission
        # May want to expand at some point to open comment permalinks
        url = self.content.get(-1)['permalink']
        open_browser(url)

    def check_content(self):
        if not self.reddit.is_logged_in():
            show_notification(self.stdscr, ["Login to add/edit/delete"])
            return None, None

        data = self.content.get(self.nav.absolute_index)
        if data['type'] == 'Submission':
            content = data['text']
        elif data['type'] == 'Comment':
            content = data['body']
        else:
            curses.flash()
            return None, None

        return data, content
        
    @SubmissionController.register('c')
    def add_comment(self):
        """
        Add a comment on the submission if a header is selected.
        Reply to a comment if the comment is selected.
        """
        data, content = self.check_content()
        if data is None:
            return

        # Comment out every line of the content
        content = '\n'.join(['# |' + line for line in content.split('\n')])
        comment_info = COMMENT_FILE.format(
            author=data['author'],
            type=data['type'].lower(),
            content=content)

        curses.endwin()
        comment_text = open_editor(comment_info)
        curses.doupdate()

        if not comment_text:
            curses.flash()
            return
        try:
            if data['type'] == 'Submission':
                data['object'].add_comment(comment_text)
            else:
                data['object'].reply(comment_text)
        except praw.errors.APIException as e:
            show_notification(self.stdscr, [e.message])
        else:
            time.sleep(2.0)
            self.refresh_content()
                    
    @SubmissionController.register('e')
    def edit_comment(self):
        """
        Edit a comment/reply on the submission if it is yours
        """

        data, content = self.check_content()
        if data is None:
            return
        
        if data['author'] != self.reddit.user.name:
            show_notification(self.stdscr, ["It is not your post"])
            return
        
        comment_info = COMMENT_EDIT_FILE.format(
            author=data['author'],
            type=data['type'].lower(),
            content=content)

        curses.endwin()
        comment_text = open_editor(comment_info)
        curses.doupdate()

        if not comment_text:
            curses.flash()
            return
        try:
            if data['type'] == 'Submission':
                data['object'].edit(comment_text)
            else:
                data['object'].edit(comment_text)
        except praw.errors.APIException as e:
            show_notification(self.stdscr, [e.message])
        else:
            time.sleep(2.0)
            self.refresh_content()
            
    @SubmissionController.register('d')
    def delete_comment(self):
        """
        Delete a selected comment/reply if it is yours.
        """
        data, content = self.check_content()
        if data is None:
            return
        
        if data['author'] != self.reddit.user.name:
            show_notification(self.stdscr, ["It is not your post"])
            return

        if 121 != show_notification(self.stdscr,
                                    ["Are you sure you want to delete "
                                     "this post? (y/n)"]):
            curses.flash()
            return
        
        try:
            data['object'].delete()
        except praw.errors.APIException as e:
            show_notification(self.stdscr, [e.message])
        else:
            time.sleep(0.5)
            self.refresh_content()

            
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

            text = clean('{author} '.format(**data))
            attr = curses.A_BOLD
            attr |= (Color.BLUE if not data['is_author'] else Color.GREEN)
            win.addnstr(row, 1, text, n_cols - 1, attr)

            if data['flair']:
                text = clean('{flair} '.format(**data))
                attr = curses.A_BOLD | Color.YELLOW
                win.addnstr(text, n_cols - win.getyx()[1], attr)

            if data['likes'] is None:
                text, attr = BULLET, curses.A_BOLD
            elif data['likes']:
                text, attr = UARROW, (curses.A_BOLD | Color.GREEN)
            else:
                text, attr = DARROW, (curses.A_BOLD | Color.RED)
            win.addnstr(text, n_cols - win.getyx()[1], attr)

            text = clean(' {score} {created}'.format(**data))
            win.addnstr(text, n_cols - win.getyx()[1])

        n_body = len(data['split_body'])
        for row, text in enumerate(data['split_body'], start=offset + 1):
            if row in valid_rows:
                text = clean(text)
                win.addnstr(row, 1, text, n_cols - 1)

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

        text = clean('{body}'.format(**data))
        win.addnstr(0, 1, text, n_cols - 1)
        text = clean(' [{count}]'.format(**data))
        win.addnstr(text, n_cols - win.getyx()[1], curses.A_BOLD)

        # Unfortunately vline() doesn't support custom color so we have to
        # build it one segment at a time.
        attr = Color.get_level(data['level'])
        win.addch(0, 0, curses.ACS_VLINE, attr)

        return (attr | curses.ACS_VLINE)

    @staticmethod
    def draw_submission(win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 3  # one for each side of the border + one for offset

        for row, text in enumerate(data['split_title'], start=1):
            text = clean(text)
            win.addnstr(row, 1, text, n_cols, curses.A_BOLD)

        row = len(data['split_title']) + 1
        attr = curses.A_BOLD | Color.GREEN
        text = clean('{author}'.format(**data))
        win.addnstr(row, 1, text, n_cols, attr)
        attr = curses.A_BOLD | Color.YELLOW
        text = clean(' {flair}'.format(**data))
        win.addnstr(text, n_cols - win.getyx()[1], attr)
        text = clean(' {created} {subreddit}'.format(**data))
        win.addnstr(text, n_cols - win.getyx()[1])

        row = len(data['split_title']) + 2
        attr = curses.A_UNDERLINE | Color.BLUE
        text = clean('{url}'.format(**data))
        win.addnstr(row, 1, text, n_cols, attr)
        offset = len(data['split_title']) + 3

        # Cut off text if there is not enough room to display the whole post
        split_text = data['split_text']
        if data['n_rows'] > n_rows:
            cutoff = data['n_rows'] - n_rows + 1
            split_text = split_text[:-cutoff]
            split_text.append('(Not enough space to display)')

        for row, text in enumerate(split_text, start=offset):
            text = clean(text)
            win.addnstr(row, 1, text, n_cols)

        row = len(data['split_title']) + len(split_text) + 3
        text = clean('{score} {comments}'.format(**data))
        win.addnstr(row, 1, text, n_cols, curses.A_BOLD)

        win.border()

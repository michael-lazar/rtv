import curses
import time
import logging
import atexit

import requests

from .exceptions import SubredditError, AccountError
from .page import BasePage, Navigator, BaseController
from .submission import SubmissionPage
from .content import SubredditContent
from .helpers import open_browser, open_editor
from .docs import SUBMISSION_FILE
from .history import load_history, save_history
from .curses_helpers import (Color, LoadScreen, add_line, get_arrow, get_gold,
                             show_notification, prompt_input)

__all__ = ['history', 'SubredditController', 'SubredditPage']
_logger = logging.getLogger(__name__)
history = load_history()


@atexit.register
def save_links():
    global history
    save_history(history)


class SubredditController(BaseController):
    character_map = {}


class SubredditPage(BasePage):

    def __init__(self, stdscr, reddit, name):

        self.controller = SubredditController(self)
        self.loader = LoadScreen(stdscr)

        content = SubredditContent.from_name(reddit, name, self.loader)
        super(SubredditPage, self).__init__(stdscr, reddit, content)

    def loop(self):
        "Main control loop"

        while True:
            self.draw()
            cmd = self.stdscr.getch()
            self.controller.trigger(cmd)

    @SubredditController.register(curses.KEY_F5, 'r')
    def refresh_content(self, name=None):
        "Re-download all submissions and reset the page index"

        name = name or self.content.name
        try:
            self.content = SubredditContent.from_name(
                self.reddit, name, self.loader)
        except AccountError:
            show_notification(self.stdscr, ['Not logged in'])
        except SubredditError:
            show_notification(self.stdscr, ['Invalid subreddit'])
        except requests.HTTPError:
            show_notification(self.stdscr, ['Could not reach subreddit'])
        else:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('f')
    def search_subreddit(self, name=None):
        "Open a prompt to search the given subreddit"

        name = name or self.content.name
        prompt = 'Search {}:'.format(name)
        query = prompt_input(self.stdscr, prompt)
        if query is None:
            return

        try:
            self.content = SubredditContent.from_name(
                self.reddit, name, self.loader, query=query)
        except IndexError:  # if there are no submissions
            show_notification(self.stdscr, ['No results found'])
        else:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('/')
    def prompt_subreddit(self):
        "Open a prompt to navigate to a different subreddit"
        prompt = 'Enter Subreddit: /r/'
        name = prompt_input(self.stdscr, prompt)
        if name is not None:
            self.refresh_content(name=name)

    @SubredditController.register(curses.KEY_RIGHT, 'l')
    def open_submission(self):
        "Select the current submission to view posts"

        data = self.content.get(self.nav.absolute_index)
        page = SubmissionPage(self.stdscr, self.reddit, url=data['permalink'])
        page.loop()

        if data['url'] == 'selfpost':
            global history
            history.add(data['url_full'])

    @SubredditController.register(curses.KEY_ENTER, 10, 'o')
    def open_link(self):
        "Open a link with the webbrowser"

        url = self.content.get(self.nav.absolute_index)['url_full']
        open_browser(url)

        global history
        history.add(url)

    @SubredditController.register('c')
    def post_submission(self):
        "Post a new submission to the given subreddit"

        if not self.reddit.is_logged_in():
            show_notification(self.stdscr, ['Not logged in'])
            return

        # Strips the subreddit to just the name
        # Make sure it is a valid subreddit for submission
        subreddit = self.reddit.get_subreddit(self.content.name)
        sub = str(subreddit).split('/')[2]
        if '+' in sub or sub in ('all', 'front', 'me'):
            show_notification(self.stdscr, ['Invalid subreddit'])
            return

        # Open the submission window
        submission_info = SUBMISSION_FILE.format(name=subreddit, content='')
        curses.endwin()
        submission_text = open_editor(submission_info)
        curses.doupdate()

        # Validate the submission content
        if not submission_text:
            show_notification(self.stdscr, ['Aborted'])
            return
        if '\n' not in submission_text:
            show_notification(self.stdscr, ['No content'])
            return

        title, content = submission_text.split('\n', 1)
        with self.safe_call as s:
            with self.loader(message='Posting', delay=0):
                post = self.reddit.submit(sub, title, text=content)
                time.sleep(2.0)
            # Open the newly created post
            s.catch = False
            page = SubmissionPage(self.stdscr, self.reddit, submission=post)
            page.loop()
            self.refresh_content()

    @staticmethod
    def draw_item(win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                add_line(win, text, row, 1, curses.A_BOLD)

        row = n_title + offset
        if row in valid_rows:
            seen = (data['url_full'] in history)
            link_color = Color.MAGENTA if seen else Color.BLUE
            attr = curses.A_UNDERLINE | link_color
            add_line(win, u'{url}'.format(**data), row, 1, attr)

        row = n_title + offset + 1
        if row in valid_rows:
            add_line(win, u'{score} '.format(**data), row, 1)
            text, attr = get_arrow(data['likes'])
            add_line(win, text, attr=attr)
            add_line(win, u' {created} {comments} '.format(**data))

            if data['gold']:
                text, attr = get_gold()
                add_line(win, text, attr=attr)

            if data['nsfw']:
                text, attr = 'NSFW', (curses.A_BOLD | Color.RED)
                add_line(win, text, attr=attr)

        row = n_title + offset + 2
        if row in valid_rows:
            add_line(win, u'{author}'.format(**data), row, 1, curses.A_BOLD)
            add_line(win, u' {subreddit}'.format(**data), attr=Color.YELLOW)
            if data['flair']:
                add_line(win, u' {flair}'.format(**data), attr=Color.RED)

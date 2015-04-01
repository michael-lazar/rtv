import curses

import requests

from .exceptions import SubredditError
from .page import BasePage, Navigator, BaseController
from .submission import SubmissionPage
from .content import SubredditContent
from .helpers import clean, open_browser
from .curses_helpers import (BULLET, UARROW, DARROW, Color, LoadScreen,
                             show_notification)

__all__ = ['opened_links', 'SubredditController', 'SubredditPage']

# Used to keep track of browsing history across the current session
opened_links = set()


class SubredditController(BaseController):
    character_map = {}


class SubredditPage(BasePage):

    def __init__(self, stdscr, reddit, name):

        self.controller = SubredditController(self)
        self.loader = LoadScreen(stdscr)

        content = SubredditContent.from_name(reddit, name, self.loader)
        super(SubredditPage, self).__init__(stdscr, reddit, content)

    def loop(self):
        while True:
            self.draw()
            cmd = self.stdscr.getch()
            self.controller.trigger(cmd)

    @SubredditController.register(curses.KEY_F5, 'r')
    def refresh_content(self, name=None):
        name = name or self.content.name

        try:
            self.content = SubredditContent.from_name(
                self.reddit, name, self.loader)
        except SubredditError:
            show_notification(self.stdscr, ['Invalid subreddit'])
        except requests.HTTPError:
            show_notification(self.stdscr, ['Could not reach subreddit'])
        else:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('f')
    def search_subreddit(self, name=None):
        """Open a prompt to search the subreddit"""
        name = name or self.content.name
        prompt = 'Search this Subreddit: '
        search = self.prompt_input(prompt)
        if search is not None:
            try:
                self.nav.cursor_index = 0
                self.content = SubredditContent.from_name(self.reddit, name,
                                                   self.loader, search=search)
            except IndexError: # if there are no submissions
                show_notification(self.stdscr, ['No results found'])

    @SubredditController.register('/')
    def prompt_subreddit(self):
        """Open a prompt to type in a new subreddit"""
        prompt = 'Enter Subreddit: /r/'
        name = self.prompt_input(prompt)
        if name is not None:
            self.refresh_content(name=name)

    @SubredditController.register(curses.KEY_RIGHT, 'l')
    def open_submission(self):
        "Select the current submission to view posts"

        data = self.content.get(self.nav.absolute_index)
        page = SubmissionPage(self.stdscr, self.reddit, url=data['permalink'])
        page.loop()

        if data['url'] == 'selfpost':
            global opened_links
            opened_links.add(data['url_full'])

    @SubredditController.register(curses.KEY_ENTER, 10, 'o')
    def open_link(self):
        "Open a link with the webbrowser"

        url = self.content.get(self.nav.absolute_index)['url_full']
        open_browser(url)

        global opened_links
        opened_links.add(url)

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
                text = clean(text)
                win.addnstr(row, 1, text, n_cols - 1, curses.A_BOLD)

        row = n_title + offset
        if row in valid_rows:
            seen = (data['url_full'] in opened_links)
            link_color = Color.MAGENTA if seen else Color.BLUE
            attr = curses.A_UNDERLINE | link_color
            text = clean('{url}'.format(**data))
            win.addnstr(row, 1, text, n_cols - 1, attr)

        row = n_title + offset + 1
        if row in valid_rows:
            text = clean('{score} '.format(**data))
            win.addnstr(row, 1, text, n_cols - 1)

            if data['likes'] is None:
                text, attr = BULLET, curses.A_BOLD
            elif data['likes']:
                text, attr = UARROW, curses.A_BOLD | Color.GREEN
            else:
                text, attr = DARROW, curses.A_BOLD | Color.RED
            win.addnstr(text, n_cols - win.getyx()[1], attr)

            text = clean(' {created} {comments}'.format(**data))
            win.addnstr(text, n_cols - win.getyx()[1])

        row = n_title + offset + 2
        if row in valid_rows:
            text = clean('{author}'.format(**data))
            win.addnstr(row, 1, text, n_cols - 1, curses.A_BOLD)
            text = clean(' {subreddit}'.format(**data))
            win.addnstr(text, n_cols - win.getyx()[1], Color.YELLOW)
            text = clean(' {flair}'.format(**data))
            win.addnstr(text, n_cols - win.getyx()[1], Color.RED)

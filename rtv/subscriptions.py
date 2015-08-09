import curses
import sys
import time
import logging

from .content import SubscriptionContent
from .page import BasePage, Navigator, BaseController
from .curses_helpers import (Color, LoadScreen, add_line)

__all__ = ['SubscriptionController', 'SubscriptionPage']
_logger = logging.getLogger(__name__)

class SubscriptionController(BaseController):
    character_map = {}

class SubscriptionPage(BasePage):
    def __init__(self, stdscr, reddit):
        self.controller = SubscriptionController(self)
        self.loader = LoadScreen(stdscr)

        content = SubscriptionContent.get_list(reddit, self.loader)
        super(SubscriptionPage, self).__init__(stdscr, reddit, content)

    def loop(self):
        "Main control loop"

        self.active = True
        while self.active:
            self.draw()
            cmd = self.stdscr.getch()
            self.controller.trigger(cmd)

    @SubscriptionController.register(curses.KEY_F5, 'r')
    def refresh_content(self):
        "Re-download all subscriptions and reset the page index"

        self.content = SubscriptionContent.get_list(self.reddit, self.loader)
        self.nav = Navigator(self.content.get)

    @SubscriptionController.register(curses.KEY_ENTER, 10)
    def open_selected_subreddit(self):
        "Open the selected subreddit"

        from .subreddit import SubredditPage
        data = self.content.get(self.nav.absolute_index)
        page = SubredditPage(self.stdscr, self.reddit, data['name'][2:]) # Strip the leading /r
        page.loop()

    @SubscriptionController.register(curses.KEY_LEFT)
    def close_subscriptions(self):
        "Close subscriptions and return to the subreddit page"

        self.active = False

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
                attr = curses.A_BOLD | Color.YELLOW
                add_line(win, u'{name}'.format(**data), row, 1, attr)

        row = n_title + offset
        if row in valid_rows:
            add_line(win, u'{title}'.format(**data), row, 1)

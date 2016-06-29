# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

from .page import Page, PageController
from .content import MultiredditContent
from .objects import Color, Navigator, Command


class SubscriptionController(PageController):
    character_map = {}


class MultiredditPage(Page):

    def __init__(self, reddit, multireddits, term, config):
        super(MultiredditPage, self).__init__(reddit, term, config, None)

        self.controller = SubscriptionController(self, keymap=config.keymap)
        self.content = MultiredditContent.from_user(reddit, multireddits,
                                                    term.loader)
        self.nav = Navigator(self.content.get)
        self.multireddit_data = None

    @SubscriptionController.register(Command('REFRESH'))
    def refresh_content(self, order=None, name=None):
        "Re-download all subscriptions and reset the page index"

        # reddit.get_multireddits() does not support sorting by order
        if order:
            self.term.flash()
            return

        with self.term.loader():
            self.content = MultiredditContent.from_user(self.reddit,
                                     self.multireddits, self.term.loader)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubscriptionController.register(Command('SUBSCRIPTION_SELECT'))
    def select_multireddit(self):
        "Store the selected multireddit and return to the subreddit page"

        self.multireddit_data = self.content.get(self.nav.absolute_index)
        self.active = False

    @SubscriptionController.register(Command('SUBSCRIPTION_EXIT'))
    def close_multireddit_subscriptions(self):
        "Close multireddits and return to the subreddit page"

        self.active = False

    def _draw_banner(self):
        # Subscriptions can't be sorted, so disable showing the order menu
        pass

    def _draw_item(self, win, data, inverted):
        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        row = offset
        if row in valid_rows:
            attr = curses.A_BOLD | Color.YELLOW
            self.term.add_line(win, '{name}'.format(**data), row, 1, attr)

        row = offset + 1
        for row, text in enumerate(data['split_title'], start=row):
            if row in valid_rows:
                self.term.add_line(win, text, row, 1)

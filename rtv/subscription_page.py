# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import docs
from .content import SubscriptionContent
from .page import Page, PageController, logged_in
from .objects import Navigator, Command


class SubscriptionController(PageController):
    character_map = {}


class SubscriptionPage(Page):
    BANNER = None
    FOOTER = docs.FOOTER_SUBSCRIPTION

    name = 'subscription'

    def __init__(self, reddit, term, config, oauth, content_type='subreddit'):
        super(SubscriptionPage, self).__init__(reddit, term, config, oauth)

        self.controller = SubscriptionController(self, keymap=config.keymap)
        self.content = SubscriptionContent.from_user(
            reddit, term.loader, content_type)
        self.nav = Navigator(self.content.get)
        self.content_type = content_type

    def handle_selected_page(self):
        """
        Always close the current page when another page is selected.
        """
        if self.selected_page:
            self.active = False

    def refresh_content(self, order=None, name=None):
        """
        Re-download all subscriptions and reset the page index
        """
        # reddit.get_my_subreddits() does not support sorting by order
        if order:
            self.term.flash()
            return

        with self.term.loader():
            self.content = SubscriptionContent.from_user(
                self.reddit, self.term.loader, self.content_type)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubscriptionController.register(Command('SUBSCRIPTION_SELECT'))
    def select_subreddit(self):
        """
        Store the selected subreddit and return to the subreddit page
        """
        name = self.get_selected_item()['name']
        self.selected_page = self.open_subreddit_page(name)

    @SubscriptionController.register(Command('SUBSCRIPTION_EXIT'))
    def close_subscriptions(self):
        """
        Close subscriptions and return to the subreddit page
        """
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
            if data['type'] == 'Multireddit':
                attr = self.term.attr('MultiredditName')
            else:
                attr = self.term.attr('SubscriptionName')
            self.term.add_line(win, '{name}'.format(**data), row, 1, attr)

        row = offset + 1
        for row, text in enumerate(data['split_title'], start=row):
            if row in valid_rows:
                if data['type'] == 'Multireddit':
                    attr = self.term.attr('MultiredditText')
                else:
                    attr = self.term.attr('SubscriptionText')
                self.term.add_line(win, text, row, 1, attr)

        attr = self.term.attr('CursorBlock')
        for y in range(n_rows):
            self.term.addch(win, y, 0, str(' '), attr)

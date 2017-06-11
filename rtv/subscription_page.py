# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

from . import docs
from .page import Page, PageController
from .content import SubscriptionContent, SubredditContent
from .objects import Color, Navigator, Command
from .packages import praw


class SubscriptionController(PageController):
    character_map = {}


class SubscriptionPage(Page):

    FOOTER = docs.FOOTER_SUBSCRIPTION

    def __init__(self, reddit, term, config, oauth, content_type='subreddit'):
        super(SubscriptionPage, self).__init__(reddit, term, config, oauth)

        self.controller = SubscriptionController(self, keymap=config.keymap)
        self.content = SubscriptionContent.from_user(
            reddit, term.loader, content_type)
        self.nav = Navigator(self.content.get)
        self.content_type = content_type
        self.selected_subreddit = None

    @SubscriptionController.register(Command('REFRESH'))
    def refresh_content(self, order=None, name=None):
        "Re-download all subscriptions and reset the page index"

        # reddit.get_my_subreddits() does not support sorting by order
        if order:
            self.term.flash()
            return

        with self.term.loader():
            self.content = SubscriptionContent.from_user(
                self.reddit, self.term.loader, self.content_type)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubscriptionController.register(Command('PROMPT'))
    def add_subreddit(self):
        "Open a prompt to add or remove multi/subreddit"

        context = self.content.name
        listing = self.get_selected_item()['object']
        name = self.term.prompt_input('Add: /')
        if name is not None:
            with self.term.loader('Adding {} to /r/{}'.format(name, context)):
                if isinstance(listing, praw.objects.Multireddit):
                    self.reddit.create_multireddit(name)
                elif hasattr(self.content, '_multireddit'):
                    self.content._multireddit.add_subreddit(name)
                elif isinstance(listing, praw.objects.Subreddit):
                    self.reddit.get_subreddit(name).subscribe()
                self.refresh_content()

    @SubscriptionController.register(Command('SUBSCRIPTION_SELECT'))
    def select_subreddit(self):
        "Store the selected subreddit and return to the subreddit page"

        name = self.get_selected_item()['name']
        with self.term.loader('Loading page'):
            content = SubredditContent.from_name(
                self.reddit, name, self.term.loader)
        if not self.term.loader.exception:
            self.selected_subreddit = content
            self.active = False

    @SubscriptionController.register(Command('SUBSCRIPTION_EXIT'))
    def close_subscriptions(self):
        "Close subscriptions and return to the subreddit page"

        self.active = False

    @SubscriptionController.register(Command('DELETE'))
    def delete_reddit(self):
        "Delete the selected reddit"

        context = self.content.name
        data = self.get_selected_item()
        listing = data['object']
        name = data['name']
        with self.term.loader('Deleting {} from {}'.format(name, context)):
            if isinstance(listing, praw.objects.Multireddit):
                modhash = self.reddit.modhash
                self.reddit.modhash = ''
                self.reddit.delete_multireddit(listing.name)
                self.reddit.modhash = modhash
            elif hasattr(self.content, '_multireddit'):
                self.content._multireddit.remove_subreddit(name)
            elif isinstance(listing, praw.objects.Subreddit):
                listing.unsubscribe()
            self.refresh_content()

    @SubscriptionController.register(Command('SUBMISSION_TOGGLE_COMMENT'))
    def open_multireddit(self):
        "View content of multireddit"

        context = self.content.name
        multi = self.get_selected_item()['object']
        if context == 'My Multireddits':
            with self.term.loader():
                self.content = SubscriptionContent.from_multireddit(
                    self.reddit, self.term.loader, multi)
            if not self.term.loader.exception:
                self.nav = Navigator(self.content.get)

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

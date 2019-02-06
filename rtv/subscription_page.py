# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from . import docs
from .packages import praw
from .page import Page, PageController
from .content import SubscriptionContent, SubredditContent
from .objects import Navigator, Command


class SubscriptionController(PageController):
    character_map = {}


class SubscriptionPage(Page):

    BANNER = None
    FOOTER = docs.FOOTER_SUBSCRIPTION

    def __init__(self, reddit, term, config, oauth, content_type='subreddit'):
        super(SubscriptionPage, self).__init__(reddit, term, config, oauth)

        self.controller = SubscriptionController(self, keymap=config.keymap)
        self.content = SubscriptionContent.from_user(
            reddit, term.loader, content_type)
        self.nav = Navigator(self.content.get)
        self.content_type = content_type
        self.selected_subreddit = None

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

    @SubscriptionController.register(Command('PROMPT'))
    def prompt_subreddit(self):
        """
        Open a prompt to navigate to a different subreddit
        """

        name = self.term.prompt_input('Enter page: /')
        if name is not None:
            with self.term.loader('Loading page'):
                content = SubredditContent.from_name(
                    self.reddit, name, self.term.loader)
            if not self.term.loader.exception:
                self.selected_subreddit = content
                self.active = False

    @SubscriptionController.register(Command('SUBSCRIPTION_SELECT'))
    def select_subreddit(self):
        """
        Store the selected subreddit and return to the subreddit page
        """

        name = self.get_selected_item()['name']
        with self.term.loader('Loading page'):
            content = SubredditContent.from_name(
                self.reddit, name, self.term.loader)
        if not self.term.loader.exception:
            self.selected_subreddit = content
            self.active = False

    @SubscriptionController.register(Command('SUBSCRIPTION_EXIT'))
    def close_subscriptions(self):
        """
        Close subscriptions and return to the subreddit page
        """

        self.active = False

    @SubscriptionController.register(Command('PROMPT_ACTION'))
    def prompt_action(self):
        choices = {
                'd': 'subscribe',
                 }
        data = self.get_selected_item()
        message = docs.SUBSCRIPTION_ACTION_MENU.format(**data).strip().splitlines()
        ch = self.term.show_notification(message)
        ch = six.unichr(ch)
        action = choices.get(ch)
        if action == 'subscribe':
            obj = data['object']
            if isinstance(obj, praw.objects.Submission):
                obj = data['object'].subreddit
            if isinstance(obj, praw.objects.Subreddit):
                self.reddit.subscribe(obj, obj.refresh().user_is_subscriber)
                msg = 'You are {}subscribed to {}'.format(
                        'no longer ' if obj.user_is_subscriber else '', obj.display_name)
                        # logic inverted to avoid addtional refresh
                self.term.show_notification(msg)
                self.reload_page()
            elif isinstance(obj, praw.objects.Multireddit) and obj.can_edit:
                msg = 'Do you really want to delete {}? (y/n): '.format(obj.display_name)
                if self.term.prompt_y_or_n(msg):
                    obj.delete()
                    self.reload_page()
        else:
            self.term.show_notification('Invalid option')

    def prompt_action(self):
        self._prompt_action(['subscribe'], docs.SUBSCRIPTION_ACTION_MENU)

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

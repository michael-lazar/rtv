# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

from . import docs
from .content import SubredditContent
from .page import Page, PageController, logged_in
from .objects import Navigator, Color, Command
from .submission_page import SubmissionPage
from .subscription_page import SubscriptionPage
from .exceptions import TemporaryFileError


class SubredditController(PageController):
    character_map = {}


class SubredditPage(Page):

    FOOTER = docs.FOOTER_SUBREDDIT

    def __init__(self, reddit, term, config, oauth, name):
        """
        Params:
            name (string): Name of subreddit to open
            url (string): Optional submission to load upon start
        """
        super(SubredditPage, self).__init__(reddit, term, config, oauth)

        self.controller = SubredditController(self, keymap=config.keymap)
        self.content = SubredditContent.from_name(reddit, name, term.loader)
        self.nav = Navigator(self.content.get)
        self.toggled_subreddit = None

    @SubredditController.register(Command('REFRESH'))
    def refresh_content(self, order=None, name=None):
        "Re-download all submissions and reset the page index"

        order = order or self.content.order
        name = name or self.content.name

        # Hack to allow an order specified in the name by prompt_subreddit() to
        # override the current default
        if order == 'ignore':
            order = None

        with self.term.loader('Refreshing page'):
            self.content = SubredditContent.from_name(
                self.reddit, name, self.term.loader, order=order)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubredditController.register(Command('SUBREDDIT_SEARCH'))
    def search_subreddit(self, name=None):
        "Open a prompt to search the given subreddit"

        name = name or self.content.name

        query = self.term.prompt_input('Search {0}: '.format(name))
        if not query:
            return

        with self.term.loader('Searching'):
            self.content = SubredditContent.from_name(
                self.reddit, name, self.term.loader, query=query)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubredditController.register(Command('PROMPT'))
    def prompt_subreddit(self):
        "Open a prompt to navigate to a different subreddit"

        name = self.term.prompt_input('Enter page: /')
        if name is not None:
            self.refresh_content(order='ignore', name=name)

    @SubredditController.register(Command('SUBREDDIT_FRONTPAGE'))
    def show_frontpage(self):
        """
        If on a subreddit, remember it and head back to the front page.
        If this was pressed on the front page, go back to the last subreddit.
        """

        if self.content.name != '/r/front':
            target = '/r/front'
            self.toggled_subreddit = self.content.name
        else:
            target = self.toggled_subreddit

        # target still may be empty string if this command hasn't yet been used
        if target is not None:
            self.refresh_content(order='ignore', name=target)

    @SubredditController.register(Command('SUBREDDIT_OPEN'))
    def open_submission(self, url=None):
        "Select the current submission to view posts"

        data = {}
        if url is None:
            data = self.content.get(self.nav.absolute_index)
            url = data['permalink']

        with self.term.loader('Loading submission'):
            page = SubmissionPage(
                self.reddit, self.term, self.config, self.oauth, url=url)
        if self.term.loader.exception:
            return

        page.loop()

        if data.get('url_type') == 'selfpost':
            self.config.history.add(data['url_full'])

        if page.selected_subreddit is not None:
            self.content = page.selected_subreddit
            self.nav = Navigator(self.content.get)

    @SubredditController.register(Command('SUBREDDIT_OPEN_IN_BROWSER'))
    def open_link(self):
        "Open a link with the webbrowser"

        data = self.content.get(self.nav.absolute_index)
        if data['url_type'] == 'selfpost':
            self.open_submission()
        elif data['url_type'] == 'x-post subreddit':
            self.refresh_content(order='ignore', name=data['xpost_subreddit'])
        elif data['url_type'] == 'x-post submission':
            self.open_submission(url=data['url_full'])
            self.config.history.add(data['url_full'])
        else:
            self.term.open_link(data['url_full'])
            self.config.history.add(data['url_full'])

    @SubredditController.register(Command('SUBREDDIT_POST'))
    @logged_in
    def post_submission(self):
        "Post a new submission to the given subreddit"

        # Check that the subreddit can be submitted to
        name = self.content.name
        if '+' in name or name in ('/r/all', '/r/front', '/r/me', '/u/saved'):
            self.term.show_notification("Can't post to {0}".format(name))
            return

        submission_info = docs.SUBMISSION_FILE.format(name=name)
        with self.term.open_editor(submission_info) as text:
            if not text:
                self.term.show_notification('Canceled')
                return
            elif '\n' not in text:
                self.term.show_notification('Missing body')
                return

            title, content = text.split('\n', 1)
            with self.term.loader('Posting', delay=0):
                submission = self.reddit.submit(name, title, text=content,
                                                raise_captcha_exception=True)
                # Give reddit time to process the submission
                time.sleep(2.0)
            if self.term.loader.exception:
                raise TemporaryFileError()

        if not self.term.loader.exception:
            # Open the newly created post
            with self.term.loader('Loading submission'):
                page = SubmissionPage(
                    self.reddit, self.term, self.config, self.oauth,
                    submission=submission)
            if self.term.loader.exception:
                return

            page.loop()

            if page.selected_subreddit is not None:
                self.content = page.selected_subreddit
                self.nav = Navigator(self.content.get)
            else:
                self.refresh_content()

    @SubredditController.register(Command('SUBREDDIT_OPEN_SUBSCRIPTIONS'))
    @logged_in
    def open_subscriptions(self):
        "Open user subscriptions page"

        with self.term.loader('Loading subscriptions'):
            page = SubscriptionPage(self.reddit, self.term, self.config,
                                    self.oauth, content_type='subreddit')
        if self.term.loader.exception:
            return

        page.loop()

        # When the user has chosen a subreddit in the subscriptions list,
        # refresh content with the selected subreddit
        if page.selected_subreddit is not None:
            self.content = page.selected_subreddit
            self.nav = Navigator(self.content.get)

    @SubredditController.register(Command('SUBREDDIT_OPEN_MULTIREDDITS'))
    @logged_in
    def open_multireddit_subscriptions(self):
        "Open user multireddit subscriptions page"

        with self.term.loader('Loading multireddits'):
            page = SubscriptionPage(self.reddit, self.term, self.config,
                                    self.oauth, content_type='multireddit')
        if self.term.loader.exception:
            return

        page.loop()

        # When the user has chosen a subreddit in the subscriptions list,
        # refresh content with the selected subreddit
        if page.selected_subreddit is not None:
            self.content = page.selected_subreddit
            self.nav = Navigator(self.content.get)

    def _draw_item(self, win, data, inverted):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                self.term.add_line(win, text, row, 1, curses.A_BOLD)

        row = n_title + offset
        if row in valid_rows:
            seen = (data['url_full'] in self.config.history)
            link_color = Color.MAGENTA if seen else Color.BLUE
            attr = curses.A_UNDERLINE | link_color
            self.term.add_line(win, '{url}'.format(**data), row, 1, attr)

        row = n_title + offset + 1
        if row in valid_rows:
            self.term.add_line(win, '{score} '.format(**data), row, 1)
            text, attr = self.term.get_arrow(data['likes'])
            self.term.add_line(win, text, attr=attr)
            self.term.add_line(win, ' {created} '.format(**data))
            text, attr = self.term.timestamp_sep
            self.term.add_line(win, text, attr=attr)
            self.term.add_line(win, ' {comments} '.format(**data))

            if data['saved']:
                text, attr = self.term.saved
                self.term.add_line(win, text, attr=attr)

            if data['stickied']:
                text, attr = self.term.stickied
                self.term.add_line(win, text, attr=attr)

            if data['gold']:
                text, attr = self.term.guilded
                self.term.add_line(win, text, attr=attr)

            if data['nsfw']:
                text, attr = 'NSFW', (curses.A_BOLD | Color.RED)
                self.term.add_line(win, text, attr=attr)

        row = n_title + offset + 2
        if row in valid_rows:
            text = '{author}'.format(**data)
            self.term.add_line(win, text, row, 1, Color.GREEN)
            text = ' /r/{subreddit}'.format(**data)
            self.term.add_line(win, text, attr=Color.YELLOW)
            if data['flair']:
                text = ' {flair}'.format(**data)
                self.term.add_line(win, text, attr=Color.RED)
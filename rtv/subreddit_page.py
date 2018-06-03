# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import time

from . import docs
from .content import SubredditContent
from .page import Page, PageController, logged_in
from .objects import Navigator, Command
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
        """
        super(SubredditPage, self).__init__(reddit, term, config, oauth)

        self.controller = SubredditController(self, keymap=config.keymap)
        self.content = SubredditContent.from_name(reddit, name, term.loader)
        self.nav = Navigator(self.content.get)
        self.toggled_subreddit = None

    def refresh_content(self, order=None, name=None):
        """
        Re-download all submissions and reset the page index
        """

        order = order or self.content.order

        # Preserve the query if staying on the current page
        if name is None:
            query = self.content.query
        else:
            query = None

        name = name or self.content.name

        # Hack to allow an order specified in the name by prompt_subreddit() to
        # override the current default
        if order == 'ignore':
            order = None

        with self.term.loader('Refreshing page'):
            self.content = SubredditContent.from_name(
                self.reddit, name, self.term.loader, order=order, query=query)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubredditController.register(Command('SORT_HOT'))
    def sort_content_hot(self):
        if self.content.query:
            self.refresh_content(order='relevance')
        else:
            self.refresh_content(order='hot')

    @SubredditController.register(Command('SORT_TOP'))
    def sort_content_top(self):
        order = self._prompt_period('top')
        if order is None:
            self.term.show_notification('Invalid option')
        else:
            self.refresh_content(order=order)

    @SubredditController.register(Command('SORT_RISING'))
    def sort_content_rising(self):
        if self.content.query:
            order = self._prompt_period('comments')
            if order is None:
                self.term.show_notification('Invalid option')
            else:
                self.refresh_content(order=order)
        else:
            self.refresh_content(order='rising')

    @SubredditController.register(Command('SORT_NEW'))
    def sort_content_new(self):
        self.refresh_content(order='new')

    @SubredditController.register(Command('SORT_CONTROVERSIAL'))
    def sort_content_controversial(self):
        if self.content.query:
            self.term.flash()
        else:
            order = self._prompt_period('controversial')
            if order is None:
                self.term.show_notification('Invalid option')
            else:
                self.refresh_content(order=order)

    @SubredditController.register(Command('SUBREDDIT_SEARCH'))
    def search_subreddit(self, name=None):
        """
        Open a prompt to search the given subreddit
        """

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
        """
        Open a prompt to navigate to a different subreddit"
        """

        name = self.term.prompt_input('Enter page: /')
        if name is not None:
            # Check if opening a submission url or a subreddit url
            # Example patterns for submissions:
            #     comments/571dw3
            #     /comments/571dw3
            #     /r/pics/comments/571dw3/
            #     https://www.reddit.com/r/pics/comments/571dw3/at_disneyland
            submission_pattern = re.compile(r'(^|/)comments/(?P<id>.+?)($|/)')

            match = submission_pattern.search(name)
            if match:
                submission_url = 'https://www.reddit.com/comments/{0}'
                self.open_submission(submission_url.format(match.group('id')))
            else:
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
        """
        Select the current submission to view posts.
        """

        data = {}
        if url is None:
            data = self.get_selected_item()
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
        """
        Open a link with the webbrowser
        """

        data = self.get_selected_item()
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
        """
        Post a new submission to the given subreddit
        """

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
                self.reload_page()

    @SubredditController.register(Command('SUBREDDIT_OPEN_SUBSCRIPTIONS'))
    @logged_in
    def open_subscriptions(self):
        """
        Open user subscriptions page
        """

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
        """
        Open user multireddit subscriptions page
        """

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

    @SubredditController.register(Command('SUBREDDIT_HIDE'))
    @logged_in
    def hide(self):
        data = self.get_selected_item()
        if not hasattr(data["object"], 'hide'):
            self.term.flash()
        elif data['hidden']:
            with self.term.loader('Unhiding'):
                data['object'].unhide()
                data['hidden'] = False
        else:
            with self.term.loader('Hiding'):
                data['object'].hide()
                data['hidden'] = True

    def _draw_item(self, win, data, inverted):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        if data['url_full'] in self.config.history:
            attr = self.term.attr('SubmissionTitleSeen')
        else:
            attr = self.term.attr('SubmissionTitle')
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                self.term.add_line(win, text, row, 1, attr)

        row = n_title + offset
        if data['url_full'] in self.config.history:
            attr = self.term.attr('LinkSeen')
        else:
            attr = self.term.attr('Link')
        if row in valid_rows:
            self.term.add_line(win, '{url}'.format(**data), row, 1, attr)

        row = n_title + offset + 1
        if row in valid_rows:

            attr = self.term.attr('Score')
            self.term.add_line(win, '{score}'.format(**data), row, 1, attr)
            self.term.add_space(win)

            arrow, attr = self.term.get_arrow(data['likes'])
            self.term.add_line(win, arrow, attr=attr)
            self.term.add_space(win)

            attr = self.term.attr('Created')
            self.term.add_line(win, '{created}'.format(**data), attr=attr)

            if data['comments'] is not None:
                attr = self.term.attr('Separator')
                self.term.add_space(win)
                self.term.add_line(win, '-', attr=attr)

                attr = self.term.attr('CommentCount')
                self.term.add_space(win)
                self.term.add_line(win, '{comments}'.format(**data), attr=attr)

            if data['saved']:
                attr = self.term.attr('Saved')
                self.term.add_space(win)
                self.term.add_line(win, '[saved]', attr=attr)

            if data['hidden']:
                attr = self.term.attr('Hidden')
                self.term.add_space(win)
                self.term.add_line(win, '[hidden]', attr=attr)

            if data['stickied']:
                attr = self.term.attr('Stickied')
                self.term.add_space(win)
                self.term.add_line(win, '[stickied]', attr=attr)

            if data['gold']:
                attr = self.term.attr('Gold')
                self.term.add_space(win)
                self.term.add_line(win, self.term.guilded, attr=attr)

            if data['nsfw']:
                attr = self.term.attr('NSFW')
                self.term.add_space(win)
                self.term.add_line(win, 'NSFW', attr=attr)

        row = n_title + offset + 2
        if row in valid_rows:
            attr = self.term.attr('SubmissionAuthor')
            self.term.add_line(win, '{author}'.format(**data), row, 1, attr)
            self.term.add_space(win)

            attr = self.term.attr('SubmissionSubreddit')
            self.term.add_line(win, '/r/{subreddit}'.format(**data), attr=attr)

            if data['flair']:
                attr = self.term.attr('SubmissionFlair')
                self.term.add_space(win)
                self.term.add_line(win, '{flair}'.format(**data), attr=attr)

        attr = self.term.attr('CursorBlock')
        for y in range(n_rows):
            self.term.addch(win, y, 0, str(' '), attr)

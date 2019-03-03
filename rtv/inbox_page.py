# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import docs
from .content import InboxContent
from .page import Page, PageController, logged_in
from .objects import Navigator, Command


class InboxController(PageController):
    character_map = {}


class InboxPage(Page):
    BANNER = docs.BANNER_INBOX
    FOOTER = docs.FOOTER_INBOX

    name = 'inbox'

    def __init__(self, reddit, term, config, oauth, content_type='all'):
        super(InboxPage, self).__init__(reddit, term, config, oauth)

        self.controller = InboxController(self, keymap=config.keymap)
        self.content = InboxContent.from_user(reddit, term.loader, content_type)
        self.nav = Navigator(self.content.get)
        self.content_type = content_type

    def handle_selected_page(self):
        """
        Open the subscription and submission pages subwindows, but close the
        current page if any other type of page is selected.
        """
        if not self.selected_page:
            pass
        if self.selected_page.name in ('subscription', 'submission'):
            # Launch page in a subwindow
            self.selected_page = self.selected_page.loop()
        elif self.selected_page.name in ('subreddit', 'inbox'):
            # Replace the current page
            self.active = False
        else:
            raise RuntimeError(self.selected_page.name)

    @logged_in
    def refresh_content(self, order=None, name=None):
        """
        Re-download all inbox content and reset the page index
        """
        self.content_type = order or self.content_type

        with self.term.loader():
            self.content = InboxContent.from_user(
                self.reddit, self.term.loader, self.content_type)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @InboxController.register(Command('SORT_1'))
    def load_content_inbox(self):
        self.refresh_content(order='all')

    @InboxController.register(Command('SORT_2'))
    def load_content_unread_messages(self):
        self.refresh_content(order='unread')

    @InboxController.register(Command('SORT_3'))
    def load_content_messages(self):
        self.refresh_content(order='messages')

    @InboxController.register(Command('SORT_4'))
    def load_content_comment_replies(self):
        self.refresh_content(order='comments')

    @InboxController.register(Command('SORT_5'))
    def load_content_post_replies(self):
        self.refresh_content(order='posts')

    @InboxController.register(Command('SORT_6'))
    def load_content_username_mentions(self):
        self.refresh_content(order='mentions')

    @InboxController.register(Command('SORT_7'))
    def load_content_sent_messages(self):
        self.refresh_content(order='sent')

    @InboxController.register(Command('INBOX_MARK_READ'))
    @logged_in
    def mark_seen(self):
        """
        Mark the selected message or comment as seen.
        """
        data = self.get_selected_item()
        if data['is_new']:
            with self.term.loader('Marking as read'):
                data['object'].mark_as_read()
            if not self.term.loader.exception:
                data['is_new'] = False
        else:
            with self.term.loader('Marking as unread'):
                data['object'].mark_as_unread()
            if not self.term.loader.exception:
                data['is_new'] = True

    @InboxController.register(Command('INBOX_REPLY'))
    @logged_in
    def inbox_reply(self):
        """
        Reply to the selected private message or comment from the inbox.
        """
        self.reply()

    @InboxController.register(Command('INBOX_EXIT'))
    def close_inbox(self):
        """
        Close inbox and return to the previous page.
        """
        self.active = False

    @InboxController.register(Command('INBOX_VIEW_CONTEXT'))
    @logged_in
    def view_context(self):
        """
        View the context surrounding the selected comment.
        """
        url = self.get_selected_item().get('context')
        if url:
            self.selected_page = self.open_submission_page(url)

    @InboxController.register(Command('INBOX_OPEN_SUBMISSION'))
    @logged_in
    def open_submission(self):
        """
        Open the full submission and comment tree for the selected comment.
        """
        url = self.get_selected_item().get('submission_permalink')
        if url:
            self.selected_page = self.open_submission_page(url)

    def _draw_item(self, win, data, inverted):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        row = offset
        if row in valid_rows:
            if data['is_new']:
                attr = self.term.attr('New')
                self.term.add_line(win, '[new]', row, 1, attr)
                self.term.add_space(win)

                attr = self.term.attr('MessageSubject')
                self.term.add_line(win, '{subject}'.format(**data), attr=attr)
                self.term.add_space(win)
            else:
                attr = self.term.attr('MessageSubject')
                self.term.add_line(win, '{subject}'.format(**data), row, 1, attr)
                self.term.add_space(win)

            if data['link_title']:
                attr = self.term.attr('MessageLink')
                self.term.add_line(win, '{link_title}'.format(**data), attr=attr)

        row = offset + 1
        if row in valid_rows:
            # reddit.user might be ``None`` if the user logs out while viewing
            # this page
            if data['author'] == getattr(self.reddit.user, 'name', None):
                self.term.add_line(win, 'to ', row, 1)
                text = '{recipient}'.format(**data)
            else:
                self.term.add_line(win, 'from ', row, 1)
                text = '{author}'.format(**data)
            attr = self.term.attr('MessageAuthor')
            self.term.add_line(win, text, attr=attr)
            self.term.add_space(win)

            if data['distinguished']:
                attr = self.term.attr('Distinguished')
                text = '[{distinguished}]'.format(**data)
                self.term.add_line(win, text, attr=attr)
                self.term.add_space(win)

            attr = self.term.attr('Created')
            text = 'sent {created_long}'.format(**data)
            self.term.add_line(win, text, attr=attr)
            self.term.add_space(win)

            if data['subreddit_name']:
                attr = self.term.attr('MessageSubreddit')
                text = 'via {subreddit_name}'.format(**data)
                self.term.add_line(win, text, attr=attr)
                self.term.add_space(win)

        attr = self.term.attr('MessageText')
        for row, text in enumerate(data['split_body'], start=offset + 2):
            if row in valid_rows:
                self.term.add_line(win, text, row, 1, attr=attr)

        attr = self.term.attr('CursorBlock')
        for y in range(n_rows):
            self.term.addch(win, y, 0, str(' '), attr)

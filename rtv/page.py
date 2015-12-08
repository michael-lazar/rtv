# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import time
import curses
from functools import wraps

from kitchen.text.display import textual_width

from . import docs
from .objects import Controller, Color


def logged_in(f):
    """
    Decorator for Page methods that require the user to be authenticated.
    """
    @wraps(f)
    def wrapped_method(self, *args, **kwargs):
        if not self.reddit.is_oauth_session():
            self.term.show_notification('Not logged in')
            return
        return f(self, *args, **kwargs)
    return wrapped_method


class PageController(Controller):
    character_map = {}


class Page(object):

    def __init__(self, reddit, term, config, oauth):

        self.reddit = reddit
        self.term = term
        self.config = config
        self.oauth = oauth
        self.content = None
        self.nav = None
        self.controller = None

        self.active = True
        self._header_window = None
        self._content_window = None
        self._subwindows = None

    def refresh_content(self, order=None, name=None):
        raise NotImplementedError

    def _draw_item(self, window, data, inverted):
        raise NotImplementedError

    def loop(self):
        """
        Main control loop runs the following steps:
            1. Re-draw the screen
            2. Wait for user to press a key (includes terminal resizing)
            3. Trigger the method registered to the input key

        The loop will run until self.active is set to False from within one of
        the methods.
        """

        self.active = True
        while self.active:
            self.draw()
            ch = self.term.stdscr.getch()
            self.controller.trigger(ch)

    @PageController.register('q')
    def exit(self):
        if self.term.prompt_y_or_n('Do you really want to quit? (y/n): '):
            sys.exit()

    @PageController.register('Q')
    def force_exit(self):
        sys.exit()

    @PageController.register('?')
    def show_help(self):
        self.term.show_notification(docs.HELP.strip().splitlines())

    @PageController.register('1')
    def sort_content_hot(self):
        self.refresh_content(order='hot')

    @PageController.register('2')
    def sort_content_top(self):
        self.refresh_content(order='top')

    @PageController.register('3')
    def sort_content_rising(self):
        self.refresh_content(order='rising')

    @PageController.register('4')
    def sort_content_new(self):
        self.refresh_content(order='new')

    @PageController.register('5')
    def sort_content_controversial(self):
        self.refresh_content(order='controversial')

    @PageController.register(curses.KEY_UP, 'k')
    def move_cursor_up(self):
        self._move_cursor(-1)
        self.clear_input_queue()

    @PageController.register(curses.KEY_DOWN, 'j')
    def move_cursor_down(self):
        self._move_cursor(1)
        self.clear_input_queue()

    @PageController.register('m', curses.KEY_PPAGE)
    def move_page_up(self):
        self._move_page(-1)
        self.clear_input_queue()

    @PageController.register('n', curses.KEY_NPAGE)
    def move_page_down(self):
        self._move_page(1)
        self.clear_input_queue()

    @PageController.register('a')
    @logged_in
    def upvote(self):
        data = self.content.get(self.nav.absolute_index)
        if 'likes' not in data:
            self.term.flash()
        elif data['likes']:
            with self.term.loader('Clearing vote'):
                data['object'].clear_vote()
            if not self.term.loader.exception:
                data['likes'] = None
        else:
            with self.term.loader('Voting'):
                data['object'].upvote()
            if not self.term.loader.exception:
                data['likes'] = True

    @PageController.register('z')
    @logged_in
    def downvote(self):
        data = self.content.get(self.nav.absolute_index)
        if 'likes' not in data:
            self.term.flash()
        elif data['likes'] or data['likes'] is None:
            with self.term.loader('Voting'):
                data['object'].downvote()
            if not self.term.loader.exception:
                data['likes'] = False
        else:
            with self.term.loader('Clearing vote'):
                data['object'].clear_vote()
            if not self.term.loader.exception:
                data['likes'] = None

    @PageController.register('u')
    def login(self):
        """
        Prompt to log into the user's account, or log out of the current
        account.
        """

        if self.reddit.is_oauth_session():
            if self.term.prompt_y_or_n('Log out? (y/n): '):
                self.oauth.clear_oauth_data()
                self.term.show_notification('Logged out')
        else:
            self.oauth.authorize()

    @PageController.register('d')
    @logged_in
    def delete_item(self):
        """
        Delete a submission or comment.
        """

        data = self.content.get(self.nav.absolute_index)
        if data.get('author') != self.reddit.user.name:
            self.term.flash()
            return

        prompt = 'Are you sure you want to delete this? (y/n): '
        if not self.term.prompt_y_or_n(prompt):
            self.term.show_notification('Canceled')
            return

        with self.term.loader('Deleting', delay=0):
            data['object'].delete()
            # Give reddit time to process the request
            time.sleep(2.0)
        if self.term.loader.exception is None:
            self.refresh_content()

    @PageController.register('e')
    @logged_in
    def edit(self):
        """
        Edit a submission or comment.
        """

        data = self.content.get(self.nav.absolute_index)
        if data.get('author') != self.reddit.user.name:
            self.term.flash()
            return

        if data['type'] == 'Submission':
            subreddit = self.reddit.get_subreddit(self.content.name)
            content = data['text']
            info = docs.SUBMISSION_EDIT_FILE.format(
                content=content, name=subreddit)
        elif data['type'] == 'Comment':
            content = data['body']
            info = docs.COMMENT_EDIT_FILE.format(content=content)
        else:
            self.term.flash()
            return

        text = self.term.open_editor(info)
        if text == content:
            self.term.show_notification('Canceled')
            return

        with self.term.loader('Editing', delay=0):
            data['object'].edit(text)
            time.sleep(2.0)
        if self.term.loader.exception is None:
            self.refresh_content()

    @PageController.register('i')
    @logged_in
    def get_inbox(self):
        """
        Checks the inbox for unread messages and displays a notification.
        """

        inbox = len(list(self.reddit.get_unread(limit=1)))
        message = 'New Messages' if inbox > 0 else 'No New Messages'
        self.term.show_notification(message)

    def clear_input_queue(self):
        """
        Clear excessive input caused by the scroll wheel or holding down a key
        """

        with self.term.no_delay():
            while self.term.getch() != -1:
                continue

    def draw(self):

        window = self.term.stdscr
        n_rows, n_cols = window.getmaxyx()
        if n_rows < self.term.MIN_HEIGHT or n_cols < self.term.MIN_WIDTH:
            # TODO: Will crash when you try to navigate if the terminal is too
            # small at startup because self._subwindows will never be populated
            return

        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        self._header_window = window.derwin(1, n_cols, 0, 0)
        self._content_window = window.derwin(n_rows - 1, n_cols, 1, 0)

        window.erase()
        self._draw_header()
        self._draw_content()
        self._add_cursor()

    def _draw_header(self):

        n_rows, n_cols = self._header_window.getmaxyx()

        self._header_window.erase()
        # curses.bkgd expects bytes in py2 and unicode in py3
        ch, attr = str(' '), curses.A_REVERSE | curses.A_BOLD | Color.CYAN
        self._header_window.bkgd(ch, attr)

        sub_name = self.content.name.replace('/r/front', 'Front Page')
        self.term.add_line(self._header_window, sub_name, 0, 0)
        if self.content.order is not None:
            order = ' [{}]'.format(self.content.order)
            self.term.add_line(self._header_window, order)

        if self.reddit.user is not None:
            # The starting position of the name depends on if we're converting
            # to ascii or not
            width = len if self.config['ascii'] else textual_width

            username = self.reddit.user.name
            s_col = (n_cols - width(username) - 1)
            # Only print username if it fits in the empty space on the right
            if (s_col - 1) >= width(sub_name):
                self.term.add_line(self._header_window, username, 0, s_col)

        self._header_window.refresh()

    def _draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """

        n_rows, n_cols = self._content_window.getmaxyx()
        self._content_window.erase()
        self._subwindows = []

        page_index, cursor_index, inverted = self.nav.position
        step = self.nav.step

        # If not inverted, align the first submission with the top and draw
        # downwards. If inverted, align the first submission with the bottom
        # and draw upwards.
        current_row = (n_rows - 1) if inverted else 0
        available_rows = (n_rows - 1) if inverted else n_rows
        for data in self.content.iterate(page_index, step, n_cols - 2):
            window_rows = min(available_rows, data['n_rows'])
            window_cols = n_cols - data['offset']
            start = current_row - window_rows if inverted else current_row
            subwindow = self._content_window.derwin(
                window_rows, window_cols, start, data['offset'])
            attr = self._draw_item(subwindow, data, inverted)
            self._subwindows.append((subwindow, attr))
            available_rows -= (window_rows + 1)  # Add one for the blank line
            current_row += step * (window_rows + 1)
            if available_rows <= 0:
                break
        else:
            # If the page is not full we need to make sure that it is NOT
            # inverted. Unfortunately, this currently means drawing the whole
            # page over again. Could not think of a better way to pre-determine
            # if the content will fill up the page, given that it is dependent
            # on the size of the terminal.
            if self.nav.inverted:
                self.nav.flip((len(self._subwindows) - 1))
                self._draw_content()

        self._content_window.refresh()

    def _add_cursor(self):
        self._edit_cursor(curses.A_REVERSE)

    def _remove_cursor(self):
        self._edit_cursor(curses.A_NORMAL)

    def _move_cursor(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            self.term.flash()

        # Note: ACS_VLINE doesn't like changing the attribute,
        # so always redraw.
        self._draw_content()
        self._add_cursor()

    def _move_page(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move_page(direction, len(self._subwindows)-1)
        if not valid:
            self.term.flash()

        # Note: ACS_VLINE doesn't like changing the attribute,
        # so always redraw.
        self._draw_content()
        self._add_cursor()

    def _edit_cursor(self, attribute):

        # Don't allow the cursor to go below page index 0
        if self.nav.absolute_index < 0:
            return

        # Don't allow the cursor to go over the number of subwindows
        # This could happen if the window is resized and the cursor index is
        # pushed out of bounds
        if self.nav.cursor_index >= len(self._subwindows):
            self.nav.cursor_index = len(self._subwindows) - 1

        window, attr = self._subwindows[self.nav.cursor_index]
        if attr is not None:
            attribute |= attr

        n_rows, _ = window.getmaxyx()
        for row in range(n_rows):
            window.chgat(row, 0, 1, attribute)

        window.refresh()
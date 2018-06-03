# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import time
import logging
from functools import wraps

import six
from kitchen.text.display import textual_width

from . import docs
from .objects import Controller, Command
from .clipboard import copy
from .exceptions import TemporaryFileError, ProgramError
from .__version__ import __version__

_logger = logging.getLogger(__name__)


def logged_in(f):
    """
    Decorator for Page methods that require the user to be authenticated.
    """

    @wraps(f)
    def wrapped_method(self, *args, **kwargs):
        if not self.reddit.is_oauth_session():
            self.term.show_notification('Not logged in')
            return None
        return f(self, *args, **kwargs)
    return wrapped_method


class PageController(Controller):
    character_map = {}


class Page(object):

    FOOTER = None

    def __init__(self, reddit, term, config, oauth):

        self.reddit = reddit
        self.term = term
        self.config = config
        self.oauth = oauth
        self.content = None
        self.nav = None
        self.controller = None
        self.copy_to_clipboard = copy

        self.active = True
        self._row = 0
        self._subwindows = None

    def refresh_content(self, order=None, name=None):
        raise NotImplementedError

    def _draw_item(self, win, data, inverted):
        raise NotImplementedError

    def get_selected_item(self):
        return self.content.get(self.nav.absolute_index)

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

    @PageController.register(Command('REFRESH'))
    def reload_page(self):
        self.reddit.handler.clear_cache()
        self.refresh_content()

    @PageController.register(Command('EXIT'))
    def exit(self):
        if self.term.prompt_y_or_n('Do you really want to quit? (y/n): '):
            sys.exit()

    @PageController.register(Command('FORCE_EXIT'))
    def force_exit(self):
        sys.exit()

    @PageController.register(Command('PREVIOUS_THEME'))
    def previous_theme(self):

        theme = self.term.theme_list.previous(self.term.theme)
        while not self.term.check_theme(theme):
            theme = self.term.theme_list.previous(theme)

        self.term.set_theme(theme)
        self.draw()
        message = self.term.theme.display_string
        self.term.show_notification(message, timeout=1)

    @PageController.register(Command('NEXT_THEME'))
    def next_theme(self):

        theme = self.term.theme_list.next(self.term.theme)
        while not self.term.check_theme(theme):
            theme = self.term.theme_list.next(theme)

        self.term.set_theme(theme)
        self.draw()
        message = self.term.theme.display_string
        self.term.show_notification(message, timeout=1)

    @PageController.register(Command('HELP'))
    def show_help(self):
        self.term.open_pager(docs.HELP.strip())

    @PageController.register(Command('MOVE_UP'))
    def move_cursor_up(self):
        self._move_cursor(-1)
        self.clear_input_queue()

    @PageController.register(Command('MOVE_DOWN'))
    def move_cursor_down(self):
        self._move_cursor(1)
        self.clear_input_queue()

    @PageController.register(Command('PAGE_UP'))
    def move_page_up(self):
        self._move_page(-1)
        self.clear_input_queue()

    @PageController.register(Command('PAGE_DOWN'))
    def move_page_down(self):
        self._move_page(1)
        self.clear_input_queue()

    @PageController.register(Command('PAGE_TOP'))
    def move_page_top(self):
        self.nav.page_index = self.content.range[0]
        self.nav.cursor_index = 0
        self.nav.inverted = False

    @PageController.register(Command('PAGE_BOTTOM'))
    def move_page_bottom(self):
        self.nav.page_index = self.content.range[1]
        self.nav.cursor_index = 0
        self.nav.inverted = True

    @PageController.register(Command('UPVOTE'))
    @logged_in
    def upvote(self):
        data = self.get_selected_item()
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

    @PageController.register(Command('DOWNVOTE'))
    @logged_in
    def downvote(self):
        data = self.get_selected_item()
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

    @PageController.register(Command('SAVE'))
    @logged_in
    def save(self):
        data = self.get_selected_item()
        if 'saved' not in data:
            self.term.flash()
        elif not data['saved']:
            with self.term.loader('Saving'):
                data['object'].save()
            if not self.term.loader.exception:
                data['saved'] = True
        else:
            with self.term.loader('Unsaving'):
                data['object'].unsave()
            if not self.term.loader.exception:
                data['saved'] = False

    @PageController.register(Command('LOGIN'))
    def login(self):
        """
        Prompt to log into the user's account, or log out of the current
        account.
        """

        if self.reddit.is_oauth_session():
            ch = self.term.show_notification('Log out? (y/n)')
            if ch in (ord('y'), ord('Y')):
                self.oauth.clear_oauth_data()
                self.term.show_notification('Logged out')
        else:
            self.oauth.authorize()

    @PageController.register(Command('DELETE'))
    @logged_in
    def delete_item(self):
        """
        Delete a submission or comment.
        """

        data = self.get_selected_item()
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
            self.reload_page()

    @PageController.register(Command('EDIT'))
    @logged_in
    def edit(self):
        """
        Edit a submission or comment.
        """

        data = self.get_selected_item()
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

        with self.term.open_editor(info) as text:
            if text == content:
                self.term.show_notification('Canceled')
                return

            with self.term.loader('Editing', delay=0):
                data['object'].edit(text)
                time.sleep(2.0)

            if self.term.loader.exception is None:
                self.reload_page()
            else:
                raise TemporaryFileError()

    @PageController.register(Command('INBOX'))
    @logged_in
    def get_inbox(self):
        """
        Checks the inbox for unread messages and displays a notification.
        """

        with self.term.loader('Loading'):
            messages = self.reddit.get_unread(limit=1)
            inbox = len(list(messages))

        if self.term.loader.exception is None:
            message = 'New Messages' if inbox > 0 else 'No New Messages'
            self.term.show_notification(message)

    @PageController.register(Command('COPY_PERMALINK'))
    def copy_permalink(self):
        """
        Copies submission permalink to OS clipboard
        """

        data = self.get_selected_item()
        url = data.get('permalink')
        if url is None:
            self.term.flash()
            return

        try:
            self.copy_to_clipboard(url)
        except (ProgramError, OSError) as e:
            _logger.exception(e)
            self.term.show_notification(
                'Failed to copy permalink: {0}'.format(e))
        else:
            self.term.show_notification(
                'Copied permalink to clipboard', timeout=1)

    @PageController.register(Command('COPY_URL'))
    def copy_url(self):
        """
        Copies submission url to OS clipboard
        """

        data = self.get_selected_item()
        url = data.get('url_full')
        if url is None:
            self.term.flash()
            return

        try:
            self.copy_to_clipboard(url)
        except (ProgramError, OSError) as e:
            _logger.exception(e)
            self.term.show_notification(
                'Failed to copy url: {0}'.format(e))
        else:
            self.term.show_notification(
                'Copied url to clipboard', timeout=1)

    def clear_input_queue(self):
        """
        Clear excessive input caused by the scroll wheel or holding down a key
        """

        with self.term.no_delay():
            while self.term.getch() != -1:
                continue

    def draw(self):

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        if n_rows < self.term.MIN_HEIGHT or n_cols < self.term.MIN_WIDTH:
            # TODO: Will crash when you try to navigate if the terminal is too
            # small at startup because self._subwindows will never be populated
            return

        self._row = 0
        self._draw_header()
        self._draw_banner()
        self._draw_content()
        self._draw_footer()
        self.term.clear_screen()
        self.term.stdscr.refresh()

    def _draw_header(self):

        n_rows, n_cols = self.term.stdscr.getmaxyx()

        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        # curses.bkgd expects bytes in py2 and unicode in py3
        window.bkgd(str(' '), self.term.attr('TitleBar'))

        sub_name = self.content.name
        sub_name = sub_name.replace('/r/front', 'Front Page')
        sub_name = sub_name.replace('/u/me', 'My Submissions')
        sub_name = sub_name.replace('/u/saved', 'My Saved Submissions')

        query = self.content.query
        if query:
            sub_name = 'Searching {0}: {1}'.format(sub_name, query)
        self.term.add_line(window, sub_name, 0, 0)

        # Set the terminal title
        if len(sub_name) > 50:
            title = sub_name.strip('/')
            title = title.rsplit('/', 1)[1]
            title = title.replace('_', ' ')
        else:
            title = sub_name

        # Setting the terminal title will break emacs or systems without
        # X window.
        if os.getenv('DISPLAY') and not os.getenv('INSIDE_EMACS'):
            title += ' - rtv {0}'.format(__version__)
            title = self.term.clean(title)
            if six.PY3:
                # In py3 you can't write bytes to stdout
                title = title.decode('utf-8')
                title = '\x1b]2;{0}\x07'.format(title)
            else:
                title = b'\x1b]2;{0}\x07'.format(title)
            sys.stdout.write(title)
            sys.stdout.flush()

        if self.reddit and self.reddit.user is not None:
            # The starting position of the name depends on if we're converting
            # to ascii or not
            width = len if self.config['ascii'] else textual_width

            if self.config['hide_username']:
                username = "Logged in"
            else:
                username = self.reddit.user.name
            s_col = (n_cols - width(username) - 1)
            # Only print username if it fits in the empty space on the right
            if (s_col - 1) >= width(sub_name):
                self.term.add_line(window, username, 0, s_col)

        self._row += 1

    def _draw_banner(self):

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        window.bkgd(str(' '), self.term.attr('OrderBar'))

        banner = docs.BANNER_SEARCH if self.content.query else docs.BANNER
        items = banner.strip().split(' ')

        distance = (n_cols - sum(len(t) for t in items) - 1) / (len(items) - 1)
        spacing = max(1, int(distance)) * ' '
        text = spacing.join(items)
        self.term.add_line(window, text, 0, 0)
        if self.content.order is not None:
            order = self.content.order.split('-')[0]
            col = text.find(order) - 3
            attr = self.term.attr('OrderBarHighlight')
            window.chgat(0, col, 3, attr)

        self._row += 1

    def _draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(n_rows - self._row - 1, n_cols, self._row, 0)
        window.erase()
        win_n_rows, win_n_cols = window.getmaxyx()

        self._subwindows = []
        page_index, cursor_index, inverted = self.nav.position
        step = self.nav.step

        # If not inverted, align the first submission with the top and draw
        # downwards. If inverted, align the first submission with the bottom
        # and draw upwards.
        cancel_inverted = True
        current_row = (win_n_rows - 1) if inverted else 0
        available_rows = win_n_rows
        top_item_height = None if inverted else self.nav.top_item_height
        for data in self.content.iterate(page_index, step, win_n_cols - 2):
            subwin_n_rows = min(available_rows, data['n_rows'])
            subwin_inverted = inverted
            if top_item_height is not None:
                # Special case: draw the page as non-inverted, except for the
                # top element. This element will be drawn as inverted with a
                # restricted height
                subwin_n_rows = min(subwin_n_rows, top_item_height)
                subwin_inverted = True
                top_item_height = None
            subwin_n_cols = win_n_cols - data['h_offset']
            start = current_row - subwin_n_rows + 1 if inverted else current_row
            subwindow = window.derwin(subwin_n_rows, subwin_n_cols, start, data['h_offset'])
            self._subwindows.append((subwindow, data, subwin_inverted))
            available_rows -= (subwin_n_rows + 1)  # Add one for the blank line
            current_row += step * (subwin_n_rows + 1)
            if available_rows <= 0:
                # Indicate the page is full and we can keep the inverted screen.
                cancel_inverted = False
                break

        if len(self._subwindows) == 1:
            # Never draw inverted if only one subwindow. The top of the
            # subwindow should always be aligned with the top of the screen.
            cancel_inverted = True

        if cancel_inverted and self.nav.inverted:
            # In some cases we need to make sure that the screen is NOT
            # inverted. Unfortunately, this currently means drawing the whole
            # page over again. Could not think of a better way to pre-determine
            # if the content will fill up the page, given that it is dependent
            # on the size of the terminal.
            self.nav.flip((len(self._subwindows) - 1))
            self._draw_content()
            return

        if self.nav.cursor_index >= len(self._subwindows):
            # Don't allow the cursor to go over the number of subwindows
            # This could happen if the window is resized and the cursor index is
            # pushed out of bounds
            self.nav.cursor_index = len(self._subwindows) - 1

        # Now that the windows are setup, we can take a second pass through
        # to draw the text onto each subwindow
        for index, (win, data, inverted) in enumerate(self._subwindows):
            if self.nav.absolute_index >= 0 and index == self.nav.cursor_index:
                win.bkgd(str(' '), self.term.attr('Selected'))
                with self.term.theme.turn_on_selected():
                    self._draw_item(win, data, inverted)
            else:
                win.bkgd(str(' '), self.term.attr('Normal'))
                self._draw_item(win, data, inverted)

        self._row += win_n_rows

    def _draw_footer(self):

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        window.bkgd(str(' '), self.term.attr('HelpBar'))

        text = self.FOOTER.strip()
        self.term.add_line(window, text, 0, 0)
        self._row += 1

    def _move_cursor(self, direction):
        # Note: ACS_VLINE doesn't like changing the attribute, so disregard the
        # redraw flag and opt to always redraw
        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            self.term.flash()

    def _move_page(self, direction):
        valid, redraw = self.nav.move_page(direction, len(self._subwindows)-1)
        if not valid:
            self.term.flash()

    def _prompt_period(self, order):

        choices = {
            '\n': order,
            '1': '{0}-hour'.format(order),
            '2': '{0}-day'.format(order),
            '3': '{0}-week'.format(order),
            '4': '{0}-month'.format(order),
            '5': '{0}-year'.format(order),
            '6': '{0}-all'.format(order)}

        message = docs.TIME_ORDER_MENU.strip().splitlines()
        ch = self.term.show_notification(message)
        ch = six.unichr(ch)
        return choices.get(ch)

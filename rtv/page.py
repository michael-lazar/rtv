# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import time
import curses
from functools import wraps

from kitchen.text.display import textual_width

from . import docs
from .objects import Controller, Color, Command


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
        self._row = 0
        self._subwindows = None

    def refresh_content(self, order=None, name=None, links_from=None):
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

    @PageController.register(Command('EXIT'))
    def exit(self):
        if self.term.prompt_y_or_n('Do you really want to quit? (y/n): '):
            sys.exit()

    @PageController.register(Command('FORCE_EXIT'))
    def force_exit(self):
        sys.exit()

    @PageController.register(Command('HELP'))
    def show_help(self):
        self.term.show_notification(docs.HELP.strip('\n').splitlines())

    @PageController.register(Command('SORT_HOT'))
    def sort_content_hot(self):
        self.refresh_content(order='hot')

    @PageController.register(Command('SORT_TOP'))
    def sort_content_top(self):
        self.refresh_content(order='top')

    @PageController.register(Command('SHOW_LINKS_FROM'))
    def show_links_from(self):
        if self.content.order not in ('top'):
            return
        ch = self.term.show_notification(
            docs.LINKS_FROM_MENU.strip('\n').splitlines())
        if ch not in range(ord('1'), ord('6') + 1):
            self.term.show_notification('Invalid option')
            return
        elif ch == ord('1'):
            order = 'hour'
        elif ch == ord('2'):
            order = 'day'
        elif ch == ord('3'):
            order = 'week'
        elif ch == ord('4'):
            order = 'month'
        elif ch == ord('5'):
            order = 'year'
        elif ch == ord('6'):
            order = 'all'

        self.refresh_content(order=self.content.order, links_from=order)

    @PageController.register(Command('SORT_RISING'))
    def sort_content_rising(self):
        self.refresh_content(order='rising')

    @PageController.register(Command('SORT_NEW'))
    def sort_content_new(self):
        self.refresh_content(order='new')

    @PageController.register(Command('SORT_CONTROVERSIAL'))
    def sort_content_controversial(self):
        self.refresh_content(order='controversial')

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

    @PageController.register(Command('UPVOTE'))
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

    @PageController.register(Command('DOWNVOTE'))
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

    @PageController.register(Command('LOGIN'))
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

    @PageController.register(Command('DELETE'))
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

    @PageController.register(Command('EDIT'))
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

    @PageController.register(Command('INBOX'))
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

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        if n_rows < self.term.MIN_HEIGHT or n_cols < self.term.MIN_WIDTH:
            # TODO: Will crash when you try to navigate if the terminal is too
            # small at startup because self._subwindows will never be populated
            return

        self._row = 0
        self._draw_header()
        self._draw_banner()
        self._draw_content()
        self._add_cursor()
        self.term.stdscr.touchwin()
        self.term.stdscr.refresh()

    def _draw_header(self):

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        # curses.bkgd expects bytes in py2 and unicode in py3
        ch, attr = str(' '), curses.A_REVERSE | curses.A_BOLD | Color.CYAN
        window.bkgd(ch, attr)

        sub_name = self.content.name.replace('/r/front', 'Front Page')
        self.term.add_line(window, sub_name, 0, 0)

        if self.reddit.user is not None:
            # The starting position of the name depends on if we're converting
            # to ascii or not
            width = len if self.config['ascii'] else textual_width

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
        ch, attr = str(' '), curses.A_BOLD | Color.YELLOW
        window.bkgd(ch, attr)

        items = ['[1]hot', '[2]top', '[3]rising', '[4]new', '[5]controversial']
        distance = (n_cols - sum(len(t) for t in items) - 1) / (len(items) - 1)
        spacing = max(1, int(distance)) * ' '
        text = spacing.join(items)
        self.term.add_line(window, text, 0, 0)
        if self.content.order is not None:
            if 'top' in self.content.order:
                col = text.find('top') - 3
            else:
                col = text.find(self.content.order) - 3
            window.chgat(0, col, 3, attr | curses.A_REVERSE)

        self._row += 1

    def _draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """

        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(
            n_rows - self._row, n_cols, self._row, 0)
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
        available_rows = (win_n_rows - 1) if inverted else win_n_rows
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
            subwin_n_cols = win_n_cols - data['offset']
            start = current_row - subwin_n_rows if inverted else current_row
            subwindow = window.derwin(
                subwin_n_rows, subwin_n_cols, start, data['offset'])
            attr = self._draw_item(subwindow, data, subwin_inverted)
            self._subwindows.append((subwindow, attr))
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

        self._row = n_rows

    def _add_cursor(self):
        self._edit_cursor(curses.A_REVERSE)

    def _remove_cursor(self):
        self._edit_cursor(curses.A_NORMAL)

    def _move_cursor(self, direction):
        self._remove_cursor()
        # Note: ACS_VLINE doesn't like changing the attribute, so disregard the
        # redraw flag and opt to always redraw
        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            self.term.flash()
        self._add_cursor()

    def _move_page(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move_page(direction, len(self._subwindows)-1)
        if not valid:
            self.term.flash()
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
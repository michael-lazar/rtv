# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

import pytest

from rtv.page import Page, PageController, PageStack, logged_in

try:
    from unittest import mock
except ImportError:
    import mock


def test_page_logged_in(terminal):

    page = mock.MagicMock()
    page.term = terminal

    @logged_in
    def func(_):
        raise RuntimeError()

    # Logged in runs the function
    page.reddit.is_oauth_session.return_value = True
    with pytest.raises(RuntimeError):
        func(page)
    message = 'Not logged in'.encode('utf-8')
    with pytest.raises(AssertionError):
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, message)

    # Logged out skips the function and displays a message
    page.reddit.is_oauth_session.return_value = False
    func(page)
    message = 'Not logged in'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_called_with(1, 1, message)


def test_page_unauthenticated(reddit, terminal, config, oauth):

    page = Page(reddit, terminal, config, oauth)
    page.controller = PageController(page, keymap=config.keymap)
    with mock.patch.object(page, 'refresh_content'), \
            mock.patch.object(page, 'content'),      \
            mock.patch.object(page, 'nav'),          \
            mock.patch.object(page, 'draw'):

        # Quit, confirm
        terminal.stdscr.getch.return_value = ord('y')
        with mock.patch('sys.exit') as sys_exit:
            page.controller.trigger('q')
        assert sys_exit.called

        # Quit, deny
        terminal.stdscr.getch.return_value = terminal.ESCAPE
        with mock.patch('sys.exit') as sys_exit:
            page.controller.trigger('q')
        assert not sys_exit.called

        # Force quit
        terminal.stdscr.getch.return_value = terminal.ESCAPE
        with mock.patch('sys.exit') as sys_exit:
            page.controller.trigger('Q')
        assert sys_exit.called

        # Show help
        with mock.patch('subprocess.Popen') as Popen:
            page.controller.trigger('?')
        assert Popen.called

        logged_in_methods = [
            'a',  # Upvote
            'z',  # Downvote
            'd',  # Delete
            'e',  # Edit
            'i',  # Get inbox
            'C',  # Private message
        ]
        for ch in logged_in_methods:
            page.controller.trigger(ch)
            message = 'Not logged in'.encode('utf-8')
            terminal.stdscr.subwin.addstr.assert_called_with(1, 1, message)
            terminal.stdscr.subwin.addstr.reset_mock()


def test_page_authenticated(reddit, terminal, config, oauth, refresh_token):

    page = Page(reddit, terminal, config, oauth)
    page.controller = PageController(page, keymap=config.keymap)
    config.refresh_token = refresh_token

    # Login
    page.controller.trigger('u')
    assert reddit.is_oauth_session()

    # Logout
    terminal.stdscr.getch.return_value = ord('y')
    page.controller.trigger('u')
    assert not reddit.is_oauth_session()


def test_page_cycle_theme(reddit, terminal, config, oauth):

    page = Page(reddit, terminal, config, oauth)
    page.controller = PageController(page, keymap=config.keymap)

    page.term.set_theme()
    assert page.term.theme.name == 'default'

    with mock.patch.object(terminal, 'show_notification'), \
            mock.patch.object(page, 'draw'):

        # Next theme
        page.controller.trigger(curses.KEY_F3)
        assert page.term.theme.name == 'monochrome'
        terminal.show_notification.assert_called_with(
            'monochrome (built-in)', timeout=1)

        # Previous theme
        page.controller.trigger(curses.KEY_F2)
        assert page.term.theme.name == 'default'
        terminal.show_notification.assert_called_with(
            'default (built-in)', timeout=1)

        # Previous - will loop to one of the 256 color themes
        page.controller.trigger(curses.KEY_F2)
        assert page.term.theme.source in ('preset', 'installed')

        # Reset
        page.term.set_theme()

        # Will skip over any installed themes that aren't supported
        curses.has_colors.return_value = False
        page.controller.trigger(curses.KEY_F2)
        assert page.term.theme.required_colors == 0


def test_page_stack(reddit, terminal, config, oauth):
    ps = PageStack(max_size=3)
    PageStack.init()

    assert PageStack.size() == 0

    # Fill the page stack:
    for _ in range(3):
        PageStack.add(Page(reddit, terminal, config, oauth))
        ps._stay_within_max_size()

    assert PageStack.size() == 3

    # Create a new page and add it to the already filled stack:
    cpage = Page(reddit, terminal, config, oauth)
    PageStack.add(cpage)
    ps._stay_within_max_size()

    assert PageStack.size() == 3
    assert PageStack.current_page() is cpage

    # Remove the currently active page 'cpage' from the stack:
    PageStack.pop()
    ps._stay_within_max_size()

    assert PageStack.size() == 2
    assert PageStack.current_page() is not cpage


def test_page_back_button(reddit, terminal, config, oauth):
    ps = PageStack(max_size=3)
    PageStack.init()

    # Add two pages to the page stack:
    page1 = Page(reddit, terminal, config, oauth)
    page1.controller = PageController(page1, keymap=config.keymap)
    page2 = Page(reddit, terminal, config, oauth)
    page2.controller = PageController(page2, keymap=config.keymap)

    for page in (page1, page2):
        PageStack.add(page)
        ps._stay_within_max_size()

    assert PageStack.size() == 2
    assert PageStack.current_page() is page2

    # Apply the back button:
    PageStack.current_page().controller.trigger('h')
    assert PageStack.size() == 1
    assert PageStack.current_page() is page1

    # Apply the back button again (page1 is the only page in the page stack):
    PageStack.current_page().controller.trigger('h')
    assert PageStack.size() == 1
    assert PageStack.current_page() is page1

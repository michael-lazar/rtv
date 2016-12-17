# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

import praw
import pytest

from rtv.subscription_page import SubscriptionPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_subscription_page_construct(reddit, terminal, config, oauth,
                                     refresh_token):
    window = terminal.stdscr.subwin

    # Log in
    config.refresh_token = refresh_token
    oauth.authorize()

    with terminal.loader():
        page = SubscriptionPage(reddit, terminal, config, oauth, 'popular')
    assert terminal.loader.exception is None

    page.draw()

    # Header - Title
    title = 'Popular Subreddits'.encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Header - Name
    name = reddit.user.name.encode('utf-8')
    assert name in [args[0][2] for args in window.addstr.call_args_list]

    # Banner shouldn't be drawn
    menu = ('[1]hot         '
            '[2]top         '
            '[3]rising         '  # Whitespace is relevant
            '[4]new         '
            '[5]controversial').encode('utf-8')
    with pytest.raises(AssertionError):
        window.addstr.assert_any_call(0, 0, menu)

    # Cursor - 2 lines
    window.subwin.chgat.assert_any_call(0, 0, 1, 262144)
    window.subwin.chgat.assert_any_call(1, 0, 1, 262144)

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = SubscriptionPage(reddit, terminal, config, oauth, 'popular')
    assert terminal.loader.exception is None

    page.draw()


def test_subscription_refresh(subscription_page):

    # Refresh content - invalid order
    subscription_page.controller.trigger('3')
    assert curses.flash.called
    curses.flash.reset_mock()

    # Refresh content
    subscription_page.controller.trigger('r')
    assert not curses.flash.called


def test_subscription_prompt(subscription_page, terminal):

    # Prompt for a different subreddit
    with mock.patch.object(terminal, 'prompt_input'):
        # Valid input
        subscription_page.active = True
        subscription_page.selected_subreddit = None
        terminal.prompt_input.return_value = 'front/top'
        subscription_page.controller.trigger('/')
        assert not subscription_page.active
        assert subscription_page.selected_subreddit

        # Invalid input
        subscription_page.active = True
        subscription_page.selected_subreddit = None
        terminal.prompt_input.return_value = 'front/pot'
        subscription_page.controller.trigger('/')
        assert subscription_page.active
        assert not subscription_page.selected_subreddit


def test_subscription_move(subscription_page):

    # Test movement
    with mock.patch.object(subscription_page, 'clear_input_queue'):

        # Move cursor down for a little while
        for _ in range(50):
            subscription_page.controller.trigger('j')
        curses.flash.reset_mock()
        assert subscription_page.nav.inverted
        assert (subscription_page.nav.absolute_index ==
                len(subscription_page.content._subscription_data) - 1)

        # And back to the top
        for i in range(subscription_page.nav.absolute_index):
            subscription_page.controller.trigger('k')
        assert not curses.flash.called
        assert subscription_page.nav.absolute_index == 0
        assert not subscription_page.nav.inverted

        # Can't go up any further
        subscription_page.controller.trigger('k')
        assert curses.flash.called
        assert subscription_page.nav.absolute_index == 0
        assert not subscription_page.nav.inverted

        # Page down should move the last item to the top
        n = len(subscription_page._subwindows)
        subscription_page.controller.trigger('n')
        assert subscription_page.nav.absolute_index == n - 1

        # And page up should move back up, but possibly not to the first item
        subscription_page.controller.trigger('m')


def test_subscription_select(subscription_page):

    # Select a subreddit
    subscription_page.controller.trigger(curses.KEY_ENTER)
    assert subscription_page.selected_subreddit is not None
    assert subscription_page.active is False


def test_subscription_close(subscription_page):

    # Close the subscriptions page
    subscription_page.selected_subreddit = None
    subscription_page.active = None
    subscription_page.controller.trigger('h')
    assert subscription_page.selected_subreddit is None
    assert subscription_page.active is False


def test_subscription_page_invalid(subscription_page, oauth, refresh_token):

    oauth.config.refresh_token = refresh_token
    oauth.authorize()

    # Test that other commands don't crash
    methods = [
        'a',  # Upvote
        'z',  # Downvote
        'd',  # Delete
        'e',  # Edit
        'w',  # Save
    ]
    for ch in methods:
        curses.flash.reset_mock()
        subscription_page.controller.trigger(ch)
        assert curses.flash.called

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

import praw
import pytest

from rtv.reddits import ListRedditsPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_list_reddits_page_construct(reddit, terminal, config,
                                     oauth, refresh_token):
    window = terminal.stdscr.subwin
    title = 'Popular Subreddits'
    func = reddit.get_popular_subreddits

    with terminal.loader():
        page = ListRedditsPage(reddit, title, func, terminal, config, oauth)
    assert terminal.loader.exception is None

    page.draw()

    # Header - Title
    window.addstr.assert_any_call(0, 0, title.encode('utf-8'))

    # Header - Name
    name = reddit.user.name.encode('utf-8')
    window.addstr.assert_any_call(0, 59, name)

    # Banner shouldn't be drawn
    menu = ('[1]hot         '
            '[2]top         '
            '[3]rising      '
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
        page = ListRedditsPage(reddit, title, func, terminal, config, oauth)
    assert terminal.loader.exception is None

    page.draw()


def test_list_reddits_refresh(list_reddits_page):

    # Refresh content - invalid order
    list_reddits_page.controller.trigger('2')
    assert curses.flash.called
    curses.flash.reset_mock()

    # Refresh content
    list_reddits_page.controller.trigger('r')
    assert not curses.flash.called


def test_list_reddits_move(list_reddits_page):

    # Test movement
    with mock.patch.object(list_reddits_page, 'clear_input_queue'):

        # Move cursor to the bottom of the page
        while not curses.flash.called:
            list_reddits_page.controller.trigger('j')
        curses.flash.reset_mock()
        assert list_reddits_page.nav.inverted
        assert (list_reddits_page.nav.absolute_index ==
                len(list_reddits_page.content._reddit_data) - 1)

        # And back to the top
        for i in range(list_reddits_page.nav.absolute_index):
            list_reddits_page.controller.trigger('k')
        assert not curses.flash.called
        assert list_reddits_page.nav.absolute_index == 0
        assert not list_reddits_page.nav.inverted

        # Can't go up any further
        list_reddits_page.controller.trigger('k')
        assert curses.flash.called
        assert list_reddits_page.nav.absolute_index == 0
        assert not list_reddits_page.nav.inverted

        # Page down should move the last item to the top
        n = len(list_reddits_page._subwindows)
        list_reddits_page.controller.trigger('n')
        assert list_reddits_page.nav.absolute_index == n - 1

        # And page up should move back up, but possibly not to the first item
        list_reddits_page.controller.trigger('m')


def test_list_reddits_select(list_reddits_page):

    # Select a subreddit
    list_reddits_page.controller.trigger(curses.KEY_ENTER)
    assert list_reddits_page.reddit_data is not None
    assert list_reddits_page.active is False


def test_list_reddits_close(list_reddits_page):

    # Close the list of reddits page
    list_reddits_page.reddit_data = None
    list_reddits_page.active = None
    list_reddits_page.controller.trigger('h')
    assert list_reddits_page.reddit_data is None
    assert list_reddits_page.active is False


def test_list_reddits_page_invalid(list_reddits_page):

    # Test that other commands don't crash
    methods = [
        'a',  # Upvote
        'z',  # Downvote
        'd',  # Delete
        'e',  # Edit
    ]
    for ch in methods:
        curses.flash.reset_mock()
        list_reddits_page.controller.trigger(ch)
        assert curses.flash.called

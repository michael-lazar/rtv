# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import curses
import logging
from functools import partial

import praw
import pytest
from vcr import VCR
from six.moves.urllib.parse import urlparse, parse_qs

from rtv.page import Page
from rtv.oauth import OAuthHelper
from rtv.config import Config
from rtv.terminal import Terminal
from rtv.subreddit import SubredditPage
from rtv.submission import SubmissionPage
from rtv.subscription import SubscriptionPage

try:
    from unittest import mock
except ImportError:
    import mock

# Turn on autospec by default for convenience
patch = partial(mock.patch, autospec=True)

# Turn on logging, but disable vcr from spamming
logging.basicConfig(level=logging.DEBUG)
for name in ['vcr.matchers', 'vcr.stubs']:
    logging.getLogger(name).disabled = True


def pytest_addoption(parser):
    parser.addoption('--record-mode', dest='record_mode', default='none')
    parser.addoption('--refresh-token', dest='refresh_token',
                     default='tests/refresh-token')


class MockStdscr(mock.MagicMock):
    """
    Extend mock to mimic curses.stdscr by keeping track of the terminal
    coordinates and allowing for the creation of subwindows with the same
    properties as stdscr.
    """

    def getyx(self):
        return self.y, self.x

    def getmaxyx(self):
        return self.nlines, self.ncols

    def derwin(self, *args):
        """
        derwin()
        derwin(begin_y, begin_x)
        derwin(nlines, ncols, begin_y, begin_x)
        """

        if 'subwin' not in dir(self):
            self.attach_mock(MockStdscr(), 'subwin')

        if len(args) == 0:
            nlines = self.nlines
            ncols = self.ncols
        elif len(args) == 2:
            nlines = self.nlines - args[0]
            ncols = self.ncols - args[1]
        else:
            nlines = min(self.nlines - args[2], args[0])
            ncols = min(self.ncols - args[3], args[1])

        self.subwin.nlines = nlines
        self.subwin.ncols = ncols
        self.subwin.x = 0
        self.subwin.y = 0
        return self.subwin


@pytest.fixture(scope='session')
def vcr(request):

    def auth_matcher(r1, r2):
        return (r1.headers.get('authorization') ==
                r2.headers.get('authorization'))

    def uri_with_query_matcher(r1, r2):
        "URI matcher that allows query params to appear in any order"
        p1,  p2 = urlparse(r1.uri), urlparse(r2.uri)
        return (p1[:3] == p2[:3] and
                parse_qs(p1.query, True) == parse_qs(p2.query, True))

    # Use `none` to use the recorded requests, and `once` to delete existing
    # cassettes and re-record.
    record_mode = request.config.option.record_mode
    assert record_mode in ('once', 'none')

    cassette_dir = os.path.join(os.path.dirname(__file__), 'cassettes')
    if not os.path.exists(cassette_dir):
        os.makedirs(cassette_dir)

    # https://github.com/kevin1024/vcrpy/pull/196
    vcr = VCR(
        record_mode=request.config.option.record_mode,
        filter_headers=[('Authorization', '**********')],
        filter_post_data_parameters=[('refresh_token', '**********')],
        match_on=['method', 'uri_with_query', 'auth', 'body'],
        cassette_library_dir=cassette_dir)
    vcr.register_matcher('auth', auth_matcher)
    vcr.register_matcher('uri_with_query', uri_with_query_matcher)
    return vcr


@pytest.fixture()
def refresh_token(request):
    if request.config.option.record_mode == 'none':
        return 'mock_refresh_token'
    else:
        return open(request.config.option.refresh_token).read()


@pytest.yield_fixture()
def config():
    with patch('rtv.config.Config.save_refresh_token'), \
            patch('rtv.config.Config.save_history'):
        yield Config()


@pytest.yield_fixture()
def stdscr():
    with patch('curses.initscr'),               \
            patch('curses.echo'),               \
            patch('curses.flash'),              \
            patch('curses.endwin'),             \
            patch('curses.newwin'),             \
            patch('curses.noecho'),             \
            patch('curses.cbreak'),             \
            patch('curses.doupdate'),           \
            patch('curses.nocbreak'),           \
            patch('curses.curs_set'),           \
            patch('curses.init_pair'),          \
            patch('curses.color_pair'),         \
            patch('curses.start_color'),        \
            patch('curses.use_default_colors'):
        out = MockStdscr(nlines=40, ncols=80, x=0, y=0)
        curses.initscr.return_value = out
        curses.newwin.side_effect = lambda *args: out.derwin(*args)
        curses.color_pair.return_value = 23
        curses.ACS_VLINE = 0
        yield out


@pytest.yield_fixture()
def reddit(vcr, request):
    cassette_name = '%s.yaml' % request.node.name
    # Clear the cassette before running the test
    if request.config.option.record_mode == 'once':
        filename = os.path.join(vcr.cassette_library_dir, cassette_name)
        if os.path.exists(filename):
            os.remove(filename)

    with vcr.use_cassette(cassette_name):
        with patch('praw.Reddit.get_access_information'):
            reddit = praw.Reddit(user_agent='rtv test suite',
                                 decode_html_entities=False,
                                 disable_update_check=True)
            if request.config.option.record_mode == 'none':
                # Turn off praw rate limiting when using cassettes
                reddit.config.api_request_delay = 0
            yield reddit


@pytest.fixture()
def terminal(stdscr, config):
    term = Terminal(stdscr, ascii=config['ascii'])
    # Disable the python 3.4 addch patch so that the mock stdscr calls are
    # always made the same way
    term.addch = lambda window, *args: window.addch(*args)
    return term


@pytest.fixture()
def oauth(reddit, terminal, config):
    return OAuthHelper(reddit, terminal, config)


@pytest.fixture()
def submission_page(reddit, terminal, config, oauth):
    submission = 'https://www.reddit.com/r/Python/comments/2xmo63'

    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=submission)
    assert terminal.loader.exception is None
    page.draw()
    return page


@pytest.fixture()
def subreddit_page(reddit, terminal, config, oauth):
    subreddit = '/r/python'

    with terminal.loader():
        page = SubredditPage(reddit, terminal, config, oauth, subreddit)
    assert not terminal.loader.exception
    page.draw()
    return page


@pytest.fixture()
def subscription_page(reddit, terminal, config, oauth, refresh_token):
    # Must be logged in to view your subscriptions
    config.refresh_token = refresh_token
    oauth.authorize()

    with terminal.loader():
        page = SubscriptionPage(reddit, terminal, config, oauth)
    assert terminal.loader.exception is None
    page.draw()
    return page

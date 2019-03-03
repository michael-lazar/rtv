# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import curses
import logging
import threading
from functools import partial

import pytest
from vcr import VCR
from six.moves.urllib.parse import urlparse, parse_qs

from rtv.oauth import OAuthHelper, OAuthHandler, OAuthHTTPServer
from rtv.content import RequestHeaderRateLimiter
from rtv.config import Config
from rtv.packages import praw
from rtv.terminal import Terminal
from rtv.subreddit_page import SubredditPage
from rtv.submission_page import SubmissionPage
from rtv.subscription_page import SubscriptionPage
from rtv.inbox_page import InboxPage

try:
    from unittest import mock
except ImportError:
    import mock

# Turn on autospec by default for convenience
patch = partial(mock.patch, autospec=True)

# Turn on logging, but disable vcr from spamming
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s')
for name in ['vcr.matchers', 'vcr.stubs']:
    logging.getLogger(name).disabled = True


def pytest_addoption(parser):
    parser.addoption('--record-mode', dest='record_mode', default='none')
    parser.addoption('--refresh-token', dest='refresh_token',
                     default='~/.local/share/rtv/refresh-token')


class MockStdscr(mock.MagicMock):
    """
    Extend mock to mimic curses.stdscr by keeping track of the terminal
    coordinates and allowing for the creation of subwindows with the same
    properties as stdscr.
    """

    def getyx(self):
        return self.y, self.x

    def getbegyx(self):
        return 0, 0

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


@pytest.fixture(scope='session')
def refresh_token(request):
    if request.config.option.record_mode == 'none':
        return 'mock_refresh_token'
    else:
        token_file = request.config.option.refresh_token
        with open(os.path.expanduser(token_file)) as fp:
            return fp.read()


@pytest.yield_fixture()
def config():
    conf = Config()
    with mock.patch.object(conf, 'save_history'),          \
            mock.patch.object(conf, 'delete_history'),     \
            mock.patch.object(conf, 'save_refresh_token'), \
            mock.patch.object(conf, 'delete_refresh_token'):
 
        def delete_refresh_token():
            # Skip the os.remove
            conf.refresh_token = None
        conf.delete_refresh_token.side_effect = delete_refresh_token

        yield conf


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
            patch('curses.has_colors'),         \
            patch('curses.start_color'),        \
            patch('curses.use_default_colors'):
        out = MockStdscr(nlines=40, ncols=80, x=0, y=0)
        curses.initscr.return_value = out
        curses.newwin.side_effect = lambda *args: out.derwin(*args)
        curses.color_pair.return_value = 23
        curses.has_colors.return_value = True
        curses.ACS_VLINE = 0
        curses.COLORS = 256
        curses.COLOR_PAIRS = 256
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
        with patch('rtv.packages.praw.Reddit.get_access_information'):
            handler = RequestHeaderRateLimiter()
            reddit = praw.Reddit(user_agent='rtv test suite',
                                 decode_html_entities=False,
                                 disable_update_check=True,
                                 handler=handler)
            # praw uses a global cache for requests, so we need to clear it
            # before each unit test. Otherwise we may fail to generate new
            # cassettes.
            reddit.handler.clear_cache()
            if request.config.option.record_mode == 'none':
                # Turn off praw rate limiting when using cassettes
                reddit.config.api_request_delay = 0
            yield reddit


@pytest.fixture()
def terminal(stdscr, config):
    term = Terminal(stdscr, config=config)
    term.set_theme()
    # Disable the python 3.4 addch patch so that the mock stdscr calls are
    # always made the same way
    term.addch = lambda window, *args: window.addch(*args)
    return term


@pytest.fixture()
def oauth(reddit, terminal, config):
    return OAuthHelper(reddit, terminal, config)


@pytest.yield_fixture()
def oauth_server():
    # Start the OAuth server on a random port in the background
    server = OAuthHTTPServer(('', 0), OAuthHandler)
    server.url = 'http://{0}:{1}/'.format(*server.server_address)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


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
def subscription_page(reddit, terminal, config, oauth):
    content_type = 'popular'

    with terminal.loader():
        page = SubscriptionPage(reddit, terminal, config, oauth, content_type)
    assert terminal.loader.exception is None
    page.draw()
    return page


@pytest.fixture()
def inbox_page(reddit, terminal, config, oauth, refresh_token):
    # The inbox page required logging in on an account with at least one message
    config.refresh_token = refresh_token
    oauth.authorize()

    with terminal.loader():
        page = InboxPage(reddit, terminal, config, oauth)
    assert terminal.loader.exception is None
    page.draw()
    return page

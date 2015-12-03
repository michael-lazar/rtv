# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase
from praw.errors import OAuthException

from rtv.oauth import OAuthHelper, OAuthHandler
from rtv.config import TEMPLATE

try:
    from unittest import mock
except ImportError:
    import mock


class TestAuthHandler(AsyncHTTPTestCase):

    def get_app(self):
        self.params = {}
        handler = [('/', OAuthHandler, {'params': self.params})]
        return Application(handler, template_path=TEMPLATE)

    def test_no_callback(self):
        resp = self.fetch('/')
        assert resp.code == 200
        assert self.params['error'] is None
        assert 'Wait...' in resp.body.decode()

    def test_access_denied(self):
        resp = self.fetch('/?error=access_denied')
        assert resp.code == 200
        assert self.params['error'] == 'access_denied'
        assert 'was denied access' in resp.body.decode()

    def test_error(self):
        resp = self.fetch('/?error=fake')
        assert resp.code == 200
        assert self.params['error'] == 'fake'
        assert 'fake' in resp.body.decode()

    def test_success(self):
        resp = self.fetch('/?state=fake_state&code=fake_code')
        assert resp.code == 200
        assert self.params['error'] is None
        assert self.params['state'] == 'fake_state'
        assert self.params['code'] == 'fake_code'
        assert 'Access Granted' in resp.body.decode()


def test_oauth_terminal_non_mobile_authorize(reddit, terminal, config):

    # Should direct to the desktop version if using a graphical browser
    reddit.config.API_PATHS['authorize'] = 'api/v1/authorize/'
    terminal._display = True
    oauth = OAuthHelper(reddit, terminal, config)
    assert '.compact' not in oauth.reddit.config.API_PATHS['authorize']


def test_oauth_terminal_mobile_authorize(reddit, terminal, config):

    # Should direct to the mobile version if using a terminal browser
    reddit.config.API_PATHS['authorize'] = 'api/v1/authorize/'
    terminal._display = False
    oauth = OAuthHelper(reddit, terminal, config)
    assert '.compact' in oauth.reddit.config.API_PATHS['authorize']


def test_oauth_authorize_with_refresh_token(oauth, stdscr, refresh_token):

    oauth.config.refresh_token = refresh_token
    oauth.authorize()
    assert oauth.http_server is None

    # We should be able to handle an oauth failure
    with mock.patch.object(oauth.reddit, 'refresh_access_information'):
        exception = OAuthException('', '')
        oauth.reddit.refresh_access_information.side_effect = exception
        oauth.authorize()
    message = 'Invalid OAuth data'.encode('utf-8')
    stdscr.derwin().addstr.assert_called_with(1, 1, message)
    assert oauth.http_server is None


def test_oauth_authorize(oauth, reddit, stdscr, refresh_token):

    # Because we use `from .helpers import open_browser` we have to patch the
    # function in the destination oauth module and not the helpers module
    with mock.patch('uuid.UUID.hex', new_callable=mock.PropertyMock) as uuid, \
            mock.patch('rtv.terminal.Terminal.open_browser') as open_browser, \
            mock.patch('rtv.oauth.ioloop') as ioloop,                         \
            mock.patch('rtv.oauth.httpserver'),                               \
            mock.patch.object(oauth.reddit, 'user'),                          \
            mock.patch('time.sleep'):
        io = ioloop.IOLoop.current.return_value

        # Valid authorization
        oauth.term._display = False
        params = {'state': 'uniqueid', 'code': 'secretcode', 'error': None}
        uuid.return_value = params['state']
        io.start.side_effect = lambda *_: oauth.params.update(**params)

        oauth.authorize()
        assert not open_browser.called
        oauth.reddit.get_access_information.assert_called_with(
            reddit, params['code'])
        assert oauth.config.refresh_token is not None
        assert oauth.config.save_refresh_token.called
        stdscr.reset_mock()
        oauth.reddit.get_access_information.reset_mock()
        oauth.config.save_refresh_token.reset_mock()
        oauth.http_server = None

        # The next authorization should skip the oauth process
        oauth.config.refresh_token = refresh_token
        oauth.authorize()
        assert oauth.reddit.user is not None
        assert oauth.http_server is None
        stdscr.reset_mock()

        # Invalid state returned
        params = {'state': 'uniqueid', 'code': 'secretcode', 'error': None}
        oauth.config.refresh_token = None
        uuid.return_value = 'invalidcode'
        oauth.authorize()
        error_message = 'UUID mismatch'.encode('utf-8')
        stdscr.subwin.addstr.assert_any_call(1, 1, error_message)

        # Valid authorization, terminal browser
        oauth.term._display = True
        params = {'state': 'uniqueid', 'code': 'secretcode', 'error': None}
        uuid.return_value = params['state']
        io.start.side_effect = lambda *_: oauth.params.update(**params)

        oauth.authorize()
        assert open_browser.called
        oauth.reddit.get_access_information.assert_called_with(
            reddit, params['code'])
        assert oauth.config.refresh_token is not None
        assert oauth.config.save_refresh_token.called
        stdscr.reset_mock()
        oauth.reddit.get_access_information.reset_mock()
        oauth.config.refresh_token = None
        oauth.config.save_refresh_token.reset_mock()
        oauth.http_server = None

        # Exceptions when logging in are handled correctly
        with mock.patch.object(oauth.reddit, 'get_access_information'):
            exception = OAuthException('', '')
            oauth.reddit.get_access_information.side_effect = exception
            oauth.authorize()
        message = 'Invalid OAuth data'.encode('utf-8')
        stdscr.derwin().addstr.assert_called_with(1, 1, message)
        assert not oauth.config.save_refresh_token.called

def test_oauth_clear_data(oauth):

    oauth.config.refresh_token = 'secrettoken'
    oauth.reddit.refresh_token = 'secrettoken'
    oauth.clear_oauth_data()
    assert oauth.config.refresh_token is None
    assert oauth.reddit.refresh_token is None
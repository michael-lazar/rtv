# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests

from rtv.oauth import OAuthHelper, OAuthHandler
from rtv.exceptions import InvalidRefreshToken
from rtv.packages.praw.errors import OAuthException


try:
    from unittest import mock
except ImportError:
    import mock


def test_oauth_handler_not_found(oauth_server):

    url = oauth_server.url + 'favicon.ico'
    resp = requests.get(url)
    assert resp.status_code == 404


def test_oauth_handler_no_callback(oauth_server):

    resp = requests.get(oauth_server.url)
    assert resp.status_code == 200
    assert 'Wait...' in resp.text
    assert OAuthHandler.params['error'] is None


def test_oauth_handler_access_denied(oauth_server):

    url = oauth_server.url + '?error=access_denied'
    resp = requests.get(url)
    assert resp.status_code == 200
    assert OAuthHandler.params['error'] == 'access_denied'
    assert 'denied access' in resp.text


def test_oauth_handler_error(oauth_server):

    url = oauth_server.url + '?error=fake'
    resp = requests.get(url)
    assert resp.status_code == 200
    assert OAuthHandler.params['error'] == 'fake'
    assert 'fake' in resp.text


def test_oauth_handler_success(oauth_server):

    url = oauth_server.url + '?state=fake_state&code=fake_code'
    resp = requests.get(url)
    assert resp.status_code == 200
    assert OAuthHandler.params['error'] is None
    assert OAuthHandler.params['state'] == 'fake_state'
    assert OAuthHandler.params['code'] == 'fake_code'
    assert 'Access Granted' in resp.text


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


def test_oauth_authorize_invalid_token(oauth):

    oauth.config.refresh_token = 'invalid_token'
    oauth.authorize()

    assert isinstance(oauth.term.loader.exception, InvalidRefreshToken)
    assert oauth.server is None
    assert oauth.config.refresh_token is None


def test_oauth_authorize_with_refresh_token(oauth, refresh_token):

    oauth.config.refresh_token = refresh_token
    oauth.authorize(autologin=True)
    assert oauth.server is None

    # We should be able to handle an oauth failure
    with mock.patch.object(oauth.reddit, 'refresh_access_information'):
        exception = OAuthException('', '')
        oauth.reddit.refresh_access_information.side_effect = exception
        oauth.authorize()

    assert isinstance(oauth.term.loader.exception, InvalidRefreshToken)
    assert oauth.server is None
    assert oauth.config.refresh_token is None


def test_oauth_authorize_without_autologin(oauth, terminal, refresh_token):

    # The welcome message should be displayed when autologin is set to
    # false, even if we're using an existing refresh token and not performing
    # the whole login procedure.
    oauth.config.refresh_token = refresh_token
    oauth.authorize(autologin=False)

    text = 'Welcome civilization_phaze_3!'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(1, 1, text)


def test_oauth_clear_data(oauth):
    oauth.config.refresh_token = 'secrettoken'
    oauth.reddit.refresh_token = 'secrettoken'
    oauth.clear_oauth_data()
    assert oauth.config.refresh_token is None
    assert oauth.reddit.refresh_token is None


def test_oauth_authorize(oauth, reddit, stdscr, refresh_token):

    # Because we use `from .helpers import open_browser` we have to patch the
    # function in the destination oauth module and not the helpers module
    with mock.patch('uuid.UUID.hex', new_callable=mock.PropertyMock) as uuid, \
            mock.patch('rtv.terminal.Terminal.open_browser') as open_browser, \
            mock.patch('rtv.oauth.OAuthHTTPServer') as http_server,           \
            mock.patch.object(oauth.reddit, 'user'),                          \
            mock.patch('time.sleep'):

        # Valid authorization
        oauth.term._display = False
        params = {'state': 'uniqueid', 'code': 'secretcode', 'error': None}
        uuid.return_value = params['state']

        def serve_forever():
            oauth.params.update(**params)
        http_server.return_value.serve_forever.side_effect = serve_forever

        oauth.authorize()
        assert open_browser.called
        oauth.reddit.get_access_information.assert_called_with(
            reddit, params['code'])
        assert oauth.config.refresh_token is not None
        assert oauth.config.save_refresh_token.called

        stdscr.reset_mock()
        oauth.reddit.get_access_information.reset_mock()
        oauth.config.save_refresh_token.reset_mock()
        oauth.server = None

        # The next authorization should skip the oauth process
        oauth.config.refresh_token = refresh_token
        oauth.authorize()
        assert oauth.reddit.user is not None
        assert oauth.server is None
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
        oauth.server = None

        # Exceptions when logging in are handled correctly
        with mock.patch.object(oauth.reddit, 'get_access_information'):
            exception = OAuthException('', '')
            oauth.reddit.get_access_information.side_effect = exception
            oauth.authorize()
        assert isinstance(oauth.term.loader.exception, OAuthException)
        assert not oauth.config.save_refresh_token.called

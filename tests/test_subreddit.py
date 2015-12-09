# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rtv.subreddit import SubredditPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_subreddit_page_construct(reddit, terminal, config, oauth):
    window = terminal.stdscr.subwin

    with terminal.loader():
        page = SubredditPage(reddit, terminal, config, oauth, '/r/python')
    assert terminal.loader.exception is None
    page.draw()

    # Title
    title = '/r/python'.encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Banner
    menu = ('[1]hot         '
            '[2]top         '
            '[3]rising         '
            '[4]new         '
            '[5]controversial').encode('utf-8')
    window.addstr.assert_any_call(0, 0, menu)

    # Submission
    text = page.content.get(0)['split_title'][0].encode('utf-8')
    window.subwin.addstr.assert_any_call(0, 1, text, 2097152)

    # Cursor should have been drawn
    assert window.subwin.chgat.called

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = SubredditPage(reddit, terminal, config, oauth, '/r/python')
    assert terminal.loader.exception is None
    page.draw()


def test_subreddit_refresh(subreddit_page, terminal):

    # Refresh the page with default values
    subreddit_page.controller.trigger('r')
    assert subreddit_page.content.order is None
    assert subreddit_page.content.name == '/r/python'
    assert terminal.loader.exception is None

    # Refresh with the order in the name
    subreddit_page.refresh_content(order='ignore', name='/r/front/hot')
    assert subreddit_page.content.order == 'hot'
    assert subreddit_page.content.name == '/r/front'
    assert terminal.loader.exception is None


def test_subreddit_search(subreddit_page, terminal):

    # Search the current subreddit
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = 'search term'
        subreddit_page.controller.trigger('f')
        assert subreddit_page.content.name == '/r/python'
        assert terminal.prompt_input.called
        assert not terminal.loader.exception

    # Searching with an empty query shouldn't crash
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = None
        subreddit_page.controller.trigger('f')
        assert not terminal.loader.exception


def test_subreddit_prompt(subreddit_page, terminal):

    # Prompt for a different subreddit
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = 'front/top'
        subreddit_page.controller.trigger('/')
        assert subreddit_page.content.name == '/r/front'
        assert subreddit_page.content.order == 'top'
        assert not terminal.loader.exception


def test_subreddit_open(subreddit_page, terminal, config):

    # Open the selected submission
    data = subreddit_page.content.get(subreddit_page.nav.absolute_index)
    with mock.patch('rtv.submission.SubmissionPage.loop') as loop, \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'selfpost'
        subreddit_page.controller.trigger('l')
        assert not terminal.loader.exception
        assert loop.called
        config.history.add.assert_called_with(data['url_full'])

    # Open the selected link externally
    with mock.patch.object(terminal, 'open_browser'), \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'external'
        subreddit_page.controller.trigger('o')
        assert terminal.open_browser.called
        config.history.add.assert_called_with(data['url_full'])

    # Open the selected link within rtv
    with mock.patch.object(subreddit_page, 'open_submission'), \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'selfpost'
        subreddit_page.controller.trigger('o')
        assert subreddit_page.open_submission.called


def test_subreddit_unauthenticated(subreddit_page, terminal):

    # Unauthenticated commands
    methods = [
        'a',  # Upvote
        'z',  # Downvote
        'c',  # Post
        'e',  # Edit
        'd',  # Delete
        's',  # Subscriptions
    ]
    for ch in methods:
        subreddit_page.controller.trigger(ch)
        text = 'Not logged in'.encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)


def test_subreddit_post(subreddit_page, terminal, reddit, refresh_token):

    # Log in
    subreddit_page.config.refresh_token = refresh_token
    subreddit_page.oauth.authorize()

    # Post a submission to an invalid subreddit
    subreddit_page.refresh_content(name='front')
    subreddit_page.controller.trigger('c')
    text = "Can't post to /r/front".encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    # Post a submission with a title but with no body
    subreddit_page.refresh_content(name='python')
    with mock.patch.object(terminal, 'open_editor'):
        terminal.open_editor.return_value = 'title'
        subreddit_page.controller.trigger('c')
        text = 'Canceled'.encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    # Post a fake submission
    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    with mock.patch.object(terminal, 'open_editor'),  \
            mock.patch.object(reddit, 'submit'),      \
            mock.patch('rtv.page.Page.loop') as loop, \
            mock.patch('time.sleep'):
        terminal.open_editor.return_value = 'test\ncontent'
        reddit.submit.return_value = submission
        subreddit_page.controller.trigger('c')
        assert reddit.submit.called
        assert loop.called


def test_subreddit_open_subscriptions(subreddit_page, refresh_token):

    # Log in
    subreddit_page.config.refresh_token = refresh_token
    subreddit_page.oauth.authorize()

    # Open a subscription
    with mock.patch('rtv.page.Page.loop') as loop:
        subreddit_page.controller.trigger('s')
        assert loop.called
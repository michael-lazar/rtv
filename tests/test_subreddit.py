# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
from praw.errors import NotFound

from rtv.subreddit_page import SubredditPage
from rtv import __version__

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


def test_subreddit_title(subreddit_page, terminal, capsys):
    subreddit_page.content.name = 'hello ❤'

    with mock.patch.dict('os.environ', {'DISPLAY': ':1'}):
        terminal.config['ascii'] = True
        subreddit_page.draw()
        out, _ = capsys.readouterr()
        assert isinstance(out, six.text_type)
        assert out == '\x1b]2;hello ? - rtv {}\x07'.format(__version__)

        terminal.config['ascii'] = False
        subreddit_page.draw()
        out, _ = capsys.readouterr()
        assert isinstance(out, six.text_type)
        assert out == '\x1b]2;hello ❤ - rtv {}\x07'.format(__version__)

    with mock.patch.dict('os.environ', {'DISPLAY': ''}):
        subreddit_page.draw()
        out, _ = capsys.readouterr()
        assert not out


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


def test_subreddit_prompt_submission(subreddit_page, terminal):

    prompts = [
        'comments/571dw3',
        '///comments/571dw3',
        '/comments/571dw3',
        '/r/pics/comments/571dw3/',
        'https://www.reddit.com/r/pics/comments/571dw3/at_disneyland']
    url = 'https://www.reddit.com/comments/571dw3'

    for text in prompts:
        with mock.patch.object(subreddit_page, 'open_submission'), \
                mock.patch.object(terminal, 'prompt_input'):

            terminal.prompt_input.return_value = text
            subreddit_page.controller.trigger('/')
            subreddit_page.open_submission.assert_called_with(url)
            assert not terminal.loader.exception


def test_subreddit_prompt_submission_invalid(subreddit_page, terminal):

    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = 'comments/571dw3fakeid'
        subreddit_page.controller.trigger('/')
        assert isinstance(terminal.loader.exception, NotFound)


def test_subreddit_order_top(subreddit_page, terminal):

    # Sort by top
    with mock.patch.object(terminal, 'show_notification'):
        # Invalid selection
        terminal.show_notification.return_value = ord('x')
        subreddit_page.controller.trigger('2')
        terminal.show_notification.assert_called_with('Invalid option')
        assert subreddit_page.content.order is None

        # Valid selection - sort by week
        terminal.show_notification.reset_mock()
        terminal.show_notification.return_value = ord('3')
        subreddit_page.controller.trigger('2')
        assert subreddit_page.content.order == 'top-week'


def test_subreddit_order_controversial(subreddit_page, terminal):

    # Sort by controversial
    with mock.patch.object(terminal, 'show_notification'):
        # Invalid selection
        terminal.show_notification.return_value = ord('x')
        subreddit_page.controller.trigger('5')
        terminal.show_notification.assert_called_with('Invalid option')
        assert subreddit_page.content.order is None

        # Valid selection - sort by default
        terminal.show_notification.reset_mock()
        terminal.show_notification.return_value = ord('\n')
        subreddit_page.controller.trigger('5')
        assert subreddit_page.content.order == 'controversial'


def test_subreddit_open(subreddit_page, terminal, config):

    # Open the selected submission
    data = subreddit_page.content.get(subreddit_page.nav.absolute_index)
    with mock.patch('rtv.submission_page.SubmissionPage.loop') as loop, \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'selfpost'
        subreddit_page.controller.trigger('l')
        assert not terminal.loader.exception
        assert loop.called
        config.history.add.assert_called_with(data['url_full'])

    # Open the selected link externally
    data = subreddit_page.content.get(subreddit_page.nav.absolute_index)
    with mock.patch.object(terminal, 'open_link'), \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'external'
        subreddit_page.controller.trigger('o')
        assert terminal.open_link.called
        config.history.add.assert_called_with(data['url_full'])

    # Open the selected link within rtv
    data = subreddit_page.content.get(subreddit_page.nav.absolute_index)
    with mock.patch.object(subreddit_page, 'open_submission'), \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'selfpost'
        subreddit_page.controller.trigger('o')
        assert subreddit_page.open_submission.called


def test_subreddit_open_xpost(subreddit_page, config):

    data = subreddit_page.content.get(subreddit_page.nav.absolute_index)

    # Open an x-post subreddit, see /r/TinySubredditoftheDay for an example
    with mock.patch.object(subreddit_page, 'refresh_content'):
        data['url_type'] = 'x-post subreddit'
        data['xpost_subreddit'] = 'goodbye'
        subreddit_page.controller.trigger('o')
        subreddit_page.refresh_content.assert_called_with(
            name='goodbye', order='ignore')

    # Open an x-post submission, see /r/bestof for an example
    with mock.patch.object(subreddit_page, 'open_submission'):
        data['url_type'] = 'x-post submission'
        data['url_full'] = 'www.test.com'
        subreddit_page.controller.trigger('o')
        subreddit_page.open_submission.assert_called_with(url='www.test.com')


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
        terminal.open_editor.return_value.__enter__.return_value = 'title'
        subreddit_page.controller.trigger('c')
        text = 'Missing body'.encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    # Post a fake submission
    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    with mock.patch.object(terminal, 'open_editor'),  \
            mock.patch.object(reddit, 'submit'),      \
            mock.patch('rtv.page.Page.loop') as loop, \
            mock.patch('time.sleep'):
        terminal.open_editor.return_value.__enter__.return_value = 'test\ncont'
        reddit.submit.return_value = submission
        subreddit_page.controller.trigger('c')
        assert reddit.submit.called
        assert loop.called


def test_subreddit_open_subscriptions(subreddit_page, refresh_token):

    # Log in
    subreddit_page.config.refresh_token = refresh_token
    subreddit_page.oauth.authorize()

    # Open subscriptions
    with mock.patch('rtv.page.Page.loop') as loop:
        subreddit_page.controller.trigger('s')
        assert loop.called


def test_subreddit_open_multireddits(subreddit_page, refresh_token):

    # Log in
    subreddit_page.config.refresh_token = refresh_token
    subreddit_page.oauth.authorize()

    # Open multireddits
    with mock.patch('rtv.page.Page.loop') as loop:
        subreddit_page.controller.trigger('S')
        assert loop.called


def test_subreddit_draw_header(subreddit_page, refresh_token, terminal):

    # /r/front alias should be renamed in the header
    subreddit_page.refresh_content(name='/r/front')
    subreddit_page.draw()
    text = 'Front Page'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(0, 0, text)

    subreddit_page.refresh_content(name='/r/front/new')
    subreddit_page.draw()
    text = 'Front Page'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(0, 0, text)

    # Log in to check the user submissions page
    subreddit_page.config.refresh_token = refresh_token
    subreddit_page.oauth.authorize()

    # /u/me alias should be renamed in the header
    subreddit_page.refresh_content(name='/u/me')
    subreddit_page.draw()
    text = 'My Submissions'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(0, 0, text)

    subreddit_page.refresh_content(name='/u/me/new')
    subreddit_page.draw()
    text = 'My Submissions'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(0, 0, text)

    # /u/saved alias should be renamed in the header
    subreddit_page.refresh_content(name='/u/saved')
    subreddit_page.draw()
    text = 'My Saved Submissions'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(0, 0, text)

    subreddit_page.refresh_content(name='/u/saved/new')
    subreddit_page.draw()
    text = 'My Saved Submissions'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(0, 0, text)


def test_subreddit_frontpage_toggle(subreddit_page, terminal):

    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = 'aww'
        subreddit_page.controller.trigger('/')
        assert subreddit_page.content.name == '/r/aww'
        subreddit_page.controller.trigger('p')
        assert subreddit_page.content.name == '/r/front'

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from rtv.packages.praw.errors import InvalidUser

from rtv import exceptions
from rtv.docs import FOOTER_INBOX
from rtv.inbox_page import InboxPage
from rtv.submission_page import SubmissionPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_inbox_page_construct(reddit, terminal, config, oauth, refresh_token):
    window = terminal.stdscr.subwin

    # This test assumes the user has at least one message in their inbox
    config.refresh_token = refresh_token
    oauth.authorize()

    with terminal.loader():
        page = InboxPage(reddit, terminal, config, oauth)
    assert terminal.loader.exception is None

    page.draw()

    #  Title
    title = 'My Inbox'.encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Banner
    menu = '[1]all  [2]unread  [3]messages  [4]comments  [5]posts  [6]mentions  [7]sent'
    window.addstr.assert_any_call(0, 0, menu.encode('utf-8'))

    # Footer - The text is longer than the default terminal width
    text = FOOTER_INBOX.strip()[:79]
    window.addstr.assert_any_call(0, 0, text.encode('utf-8'))

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = InboxPage(reddit, terminal, config, oauth)
    assert terminal.loader.exception is None
    page.draw()


def test_inbox_private_message_parse_file(inbox_page, terminal, reddit):

    with mock.patch.object(terminal, 'open_editor') as open_editor, \
            mock.patch.object(reddit, 'send_message') as send_message, \
            mock.patch('time.sleep'):

        text = ''
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('C')
        assert not send_message.called

        text = 'civilization_phaze_3'
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('C')
        assert not send_message.called

        text = 'civilization_phaze_3\n'
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('C')
        assert not send_message.called

        text = 'civilization_phaze_3\nsubject'
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('C')
        assert not send_message.called

        text = 'civilization_phaze_3\nsubject\n '
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('C')
        assert not send_message.called

        text = 'civilization_phaze_3\nsubject\nbody\n'
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('C')
        send_message.assert_called_with(
            'civilization_phaze_3', 'subject', 'body',
            raise_captcha_exception=True)


def test_inbox_private_message_invalid_author(inbox_page, terminal):

    with mock.patch.object(terminal, 'open_editor') as open_editor:
        text = 'u34891034hjui9oshcvasu7dfashiudhji1293801jdka\nsubject\nbody\n'
        open_editor.return_value.__enter__.return_value = text

        with pytest.raises(exceptions.TemporaryFileError):
            inbox_page.controller.trigger('C')

        assert isinstance(terminal.loader.exception, InvalidUser)


def test_inbox_reply_message(inbox_page, terminal):

    # View messages - this test requires at least one private message
    inbox_page.controller.trigger('3')

    msg = inbox_page.get_selected_item()['object']

    with mock.patch.object(terminal, 'open_editor') as open_editor, \
            mock.patch.object(msg, 'reply') as reply, \
            mock.patch('time.sleep'):

        text = 'My response text'
        open_editor.return_value.__enter__.return_value = text
        inbox_page.controller.trigger('c')
        reply.assert_called_with(text)


def test_inbox_mark_seen(inbox_page, terminal):

    data = inbox_page.get_selected_item()
    message = data['object']

    # Test save on the submission
    with mock.patch.object(message, 'mark_as_read') as mark_as_read, \
            mock.patch.object(message, 'mark_as_unread') as mark_as_unread:

        data['is_new'] = True

        # Mark as seen
        inbox_page.controller.trigger('w')
        assert mark_as_read.called
        assert data['is_new'] is False

        # Mark as no seen
        inbox_page.controller.trigger('w')
        assert mark_as_unread.called
        assert data['is_new'] is True

        # If an exception is raised, state should not be changed
        mark_as_read.side_effect = KeyboardInterrupt
        inbox_page.controller.trigger('w')
        assert data['is_new'] is True


def test_inbox_close(inbox_page, terminal):

    inbox_page.active = None
    inbox_page.controller.trigger('h')
    assert inbox_page.active is False


def test_inbox_view_context(inbox_page, terminal):

    # Should be able to view the context of a comment
    inbox_page.controller.trigger('4')
    inbox_page.controller.trigger('l')
    assert inbox_page.active
    assert inbox_page.selected_page
    assert isinstance(inbox_page.selected_page, SubmissionPage)

    inbox_page.selected_page = None

    # Should not be able to view the context of a private message
    inbox_page.controller.trigger('3')
    inbox_page.controller.trigger('l')
    assert inbox_page.active
    assert inbox_page.selected_page is None
    assert terminal.loader.exception is None


def test_inbox_open_submission(inbox_page, terminal):

    # Should be able to open the submission that a comment was for
    inbox_page.controller.trigger('4')
    inbox_page.controller.trigger('o')
    assert inbox_page.active
    assert inbox_page.selected_page
    assert isinstance(inbox_page.selected_page, SubmissionPage)

    inbox_page.selected_page = None

    # Should not be able to open the submission for a private message
    inbox_page.controller.trigger('3')
    inbox_page.controller.trigger('o')
    assert inbox_page.active
    assert inbox_page.selected_page is None
    assert terminal.loader.exception is None

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

from rtv.submission_page import SubmissionPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_submission_page_construct(reddit, terminal, config, oauth):
    window = terminal.stdscr.subwin
    url = ('https://www.reddit.com/r/Python/comments/2xmo63/'
           'a_python_terminal_viewer_for_browsing_reddit')

    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=url)
    assert terminal.loader.exception is None

    # Toggle the second comment so we can check the draw more comments method
    page.content.toggle(1)

    # Set some special flags to make sure that we can draw them
    submission_data = page.content.get(-1)
    submission_data['gold'] = True
    submission_data['stickied'] = True
    submission_data['saved'] = True
    submission_data['flair'] = 'flair'

    # Set some special flags to make sure that we can draw them
    comment_data = page.content.get(0)
    comment_data['gold'] = True
    comment_data['stickied'] = True
    comment_data['saved'] = True
    comment_data['flair'] = 'flair'

    page.draw()

    #  Title
    title = url[:terminal.stdscr.ncols-1].encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Banner
    menu = ('[1]hot         '
            '[2]top         '
            '[3]rising         '
            '[4]new         '
            '[5]controversial').encode('utf-8')
    window.addstr.assert_any_call(0, 0, menu)

    # Footer
    text = ('[?]Help [q]Quit [h]Return [space]Fold/Expand [o]Open [c]Comment '
            '[a/z]Vote'.encode('utf-8'))
    window.addstr.assert_any_call(0, 0, text)

    # Submission
    submission_data = page.content.get(-1)
    text = submission_data['title'].encode('utf-8')
    window.subwin.addstr.assert_any_call(1, 1, text, 2097152)
    assert window.subwin.border.called

    # Comment
    comment_data = page.content.get(0)
    text = comment_data['split_body'][0].encode('utf-8')
    window.subwin.addstr.assert_any_call(1, 1, text)

    # More Comments
    comment_data = page.content.get(1)
    text = comment_data['body'].encode('utf-8')
    window.subwin.addstr.assert_any_call(0, 1, text)

    # Cursor should not be drawn when the page is first opened
    assert not window.subwin.chgat.called

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=url)
    assert terminal.loader.exception is None
    page.draw()


def test_submission_refresh(submission_page):

    # Should be able to refresh content
    submission_page.refresh_content()


def test_submission_exit(submission_page):

    # Exiting should set active to false
    submission_page.active = True
    submission_page.controller.trigger('h')
    assert not submission_page.active


def test_submission_unauthenticated(submission_page, terminal):

    # Unauthenticated commands
    methods = [
        'a',  # Upvote
        'z',  # Downvote
        'c',  # Comment
        'e',  # Edit
        'd',  # Delete
        'w',  # Save
    ]
    for ch in methods:
        submission_page.controller.trigger(ch)
        text = 'Not logged in'.encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)


def test_submission_open(submission_page, terminal):

    # Open the selected link with the web browser
    with mock.patch.object(terminal, 'open_browser'):
        submission_page.controller.trigger(terminal.RETURN)
        assert terminal.open_browser.called


def test_submission_prompt(submission_page, terminal):

    # Prompt for a different subreddit
    with mock.patch.object(terminal, 'prompt_input'):
        # Valid input
        submission_page.active = True
        submission_page.selected_subreddit = None
        terminal.prompt_input.return_value = 'front/top'
        submission_page.controller.trigger('/')
        assert not submission_page.active
        assert submission_page.selected_subreddit

        # Invalid input
        submission_page.active = True
        submission_page.selected_subreddit = None
        terminal.prompt_input.return_value = 'front/pot'
        submission_page.controller.trigger('/')
        assert submission_page.active
        assert not submission_page.selected_subreddit


def test_submission_order_top(submission_page, terminal):

    # Sort by top - First time selects default
    submission_page.controller.trigger('2')
    assert submission_page.content.order == 'top'

    # Second time opens the menu
    with mock.patch.object(terminal, 'show_notification'):
        # Invalid selection
        terminal.show_notification.return_value = ord('x')
        submission_page.controller.trigger('2')
        terminal.show_notification.assert_called_with('Invalid option')
        assert submission_page.content.order == 'top'

        # Valid selection - sort by week
        terminal.show_notification.reset_mock()
        terminal.show_notification.return_value = ord('3')
        submission_page.controller.trigger('2')
        assert submission_page.content.order == 'top-week'


def test_submission_order_controversial(submission_page, terminal):

    # Now do controversial
    submission_page.controller.trigger('5')
    assert submission_page.content.order == 'controversial'

    with mock.patch.object(terminal, 'show_notification'):
        # Invalid selection
        terminal.show_notification.return_value = ord('x')
        submission_page.controller.trigger('5')
        terminal.show_notification.assert_called_with('Invalid option')
        assert submission_page.content.order == 'controversial'

        # Valid selection - sort by week
        terminal.show_notification.reset_mock()
        terminal.show_notification.return_value = ord('3')
        submission_page.controller.trigger('5')
        assert submission_page.content.order == 'controversial-week'


def test_submission_move_top_bottom(submission_page):

    submission_page.controller.trigger('G')
    assert submission_page.nav.absolute_index == 44

    submission_page.controller.trigger('g')
    submission_page.controller.trigger('g')
    assert submission_page.nav.absolute_index == -1


def test_submission_pager(submission_page, terminal):

    # View a submission with the pager
    with mock.patch.object(terminal, 'open_pager'):
        submission_page.controller.trigger('l')
        assert terminal.open_pager.called

    # Move down to the first comment
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')

    # View a comment with the pager
    with mock.patch.object(terminal, 'open_pager'):
        submission_page.controller.trigger('l')
        assert terminal.open_pager.called


def test_submission_comment_not_enough_space(submission_page, terminal):

    # The first comment is 10 lines, shrink the screen so that it won't fit.
    # Setting the terminal to 10 lines means that there will only be 8 lines
    # available (after subtracting the header and footer) to draw the comment.
    terminal.stdscr.nlines = 10

    # Select the first comment
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.move_cursor_down()

    submission_page.draw()

    text = '(Not enough space to display)'.encode('ascii')
    window = terminal.stdscr.subwin
    window.subwin.addstr.assert_any_call(6, 1, text)


def test_submission_vote(submission_page, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Test voting on the submission
    with mock.patch('praw.objects.Submission.upvote') as upvote,            \
            mock.patch('praw.objects.Submission.downvote') as downvote,     \
            mock.patch('praw.objects.Submission.clear_vote') as clear_vote:

        data = submission_page.content.get(submission_page.nav.absolute_index)

        # Upvote
        submission_page.controller.trigger('a')
        assert upvote.called
        assert data['likes'] is True

        # Clear vote
        submission_page.controller.trigger('a')
        assert clear_vote.called
        assert data['likes'] is None

        # Upvote
        submission_page.controller.trigger('a')
        assert upvote.called
        assert data['likes'] is True

        # Downvote
        submission_page.controller.trigger('z')
        assert downvote.called
        assert data['likes'] is False

        # Clear vote
        submission_page.controller.trigger('z')
        assert clear_vote.called
        assert data['likes'] is None

        # Upvote - exception
        upvote.side_effect = KeyboardInterrupt
        submission_page.controller.trigger('a')
        assert data['likes'] is None

        # Downvote - exception
        downvote.side_effect = KeyboardInterrupt
        submission_page.controller.trigger('a')
        assert data['likes'] is None


def test_submission_save(submission_page, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Test save on the submission
    with mock.patch('praw.objects.Submission.save') as save,        \
            mock.patch('praw.objects.Submission.unsave') as unsave:

        data = submission_page.content.get(submission_page.nav.absolute_index)

        # Save
        submission_page.controller.trigger('w')
        assert save.called
        assert data['saved'] is True

        # Unsave
        submission_page.controller.trigger('w')
        assert unsave.called
        assert data['saved'] is False

        # Save - exception
        save.side_effect = KeyboardInterrupt
        submission_page.controller.trigger('w')
        assert data['saved'] is False


def test_submission_comment_save(submission_page, terminal, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Move down to the first comment
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')

    # Test save on the coment submission
    with mock.patch('praw.objects.Comment.save') as save,        \
            mock.patch('praw.objects.Comment.unsave') as unsave:

        data = submission_page.content.get(submission_page.nav.absolute_index)

        # Save
        submission_page.controller.trigger('w')
        assert save.called
        assert data['saved'] is True

        # Unsave
        submission_page.controller.trigger('w')
        assert unsave.called
        assert data['saved'] is False

        # Save - exception
        save.side_effect = KeyboardInterrupt
        submission_page.controller.trigger('w')
        assert data['saved'] is False


def test_submission_comment(submission_page, terminal, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Leave a comment
    with mock.patch('praw.objects.Submission.add_comment') as add_comment, \
            mock.patch.object(terminal, 'open_editor') as open_editor,     \
            mock.patch('time.sleep'):
        open_editor.return_value.__enter__.return_value = 'comment text'
        submission_page.controller.trigger('c')
        assert open_editor.called
        add_comment.assert_called_with('comment text')


def test_submission_delete(submission_page, terminal, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Can't delete the submission
    curses.flash.reset_mock()
    submission_page.controller.trigger('d')
    assert curses.flash.called

    # Move down to the first comment
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')

    # Try to delete the first comment - wrong author
    curses.flash.reset_mock()
    submission_page.controller.trigger('d')
    assert curses.flash.called

    # Spoof the author and try to delete again
    data = submission_page.content.get(submission_page.nav.absolute_index)
    data['author'] = submission_page.reddit.user.name
    with mock.patch('praw.objects.Comment.delete') as delete,     \
            mock.patch.object(terminal.stdscr, 'getch') as getch, \
            mock.patch('time.sleep'):
        getch.return_value = ord('y')
        submission_page.controller.trigger('d')
        assert delete.called


def test_submission_edit(submission_page, terminal, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Try to edit the submission - wrong author
    data = submission_page.content.get(submission_page.nav.absolute_index)
    data['author'] = 'some other person'
    curses.flash.reset_mock()
    submission_page.controller.trigger('e')
    assert curses.flash.called

    # Spoof the submission and try to edit again
    data = submission_page.content.get(submission_page.nav.absolute_index)
    data['author'] = submission_page.reddit.user.name
    with mock.patch('praw.objects.Submission.edit') as edit,           \
            mock.patch.object(terminal, 'open_editor') as open_editor, \
            mock.patch('time.sleep'):
        open_editor.return_value.__enter__.return_value = 'submission text'

        submission_page.controller.trigger('e')
        assert open_editor.called
        edit.assert_called_with('submission text')

    # Move down to the first comment
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')

    # Spoof the author and edit the comment
    data = submission_page.content.get(submission_page.nav.absolute_index)
    data['author'] = submission_page.reddit.user.name
    with mock.patch('praw.objects.Comment.edit') as edit,              \
            mock.patch.object(terminal, 'open_editor') as open_editor, \
            mock.patch('time.sleep'):
        open_editor.return_value.__enter__.return_value = 'comment text'

        submission_page.controller.trigger('e')
        assert open_editor.called
        edit.assert_called_with('comment text')


def test_submission_urlview(submission_page, terminal, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Submission case
    data = submission_page.content.get(submission_page.nav.absolute_index)
    data['body'] = 'test comment body  ❤'
    with mock.patch.object(terminal, 'open_urlview') as open_urlview:
        submission_page.controller.trigger('b')
        open_urlview.assert_called_with('test comment body  ❤')

    # Subreddit case
    data = submission_page.content.get(submission_page.nav.absolute_index)
    data['text'] = ''
    data['body'] = ''
    data['url_full'] = 'http://test.url.com  ❤'
    with mock.patch.object(terminal, 'open_urlview') as open_urlview, \
            mock.patch('subprocess.Popen'):
        submission_page.controller.trigger('b')
        open_urlview.assert_called_with('http://test.url.com  ❤')

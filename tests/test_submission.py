# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses
from collections import OrderedDict

import pytest

from rtv.submission_page import SubmissionPage
from rtv.docs import FOOTER_SUBMISSION

try:
    from unittest import mock
except ImportError:
    import mock


PROMPTS = OrderedDict([
    ('prompt_1', 'comments/571dw3'),
    ('prompt_2', '///comments/571dw3'),
    ('prompt_3', '/comments/571dw3'),
    ('prompt_4', '/r/pics/comments/571dw3/'),
    ('prompt_5', 'https://www.reddit.com/r/pics/comments/571dw3/at_disneyland'),
])


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
    submission_data['gold'] = 1
    submission_data['stickied'] = True
    submission_data['saved'] = True
    submission_data['flair'] = 'flair'

    # Set some special flags to make sure that we can draw them
    comment_data = page.content.get(0)
    comment_data['gold'] = 3
    comment_data['stickied'] = True
    comment_data['saved'] = True
    comment_data['flair'] = 'flair'

    page.draw()

    #  Title
    title = url[:terminal.stdscr.ncols-1].encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Banner
    menu = '[1]hot         [2]top         [3]rising         [4]new         [5]controversial'
    window.addstr.assert_any_call(0, 0, menu.encode('utf-8'))

    # Footer - The text is longer than the default terminal width
    text = FOOTER_SUBMISSION.strip()[:79]
    window.addstr.assert_any_call(0, 0, text.encode('utf-8'))

    # Submission
    submission_data = page.content.get(-1)
    text = submission_data['title'].encode('utf-8')
    window.subwin.addstr.assert_any_call(1, 1, text, 2097152)
    assert window.subwin.border.called

    # Comment
    comment_data = page.content.get(0)
    text = comment_data['split_body'][0].encode('utf-8')
    window.subwin.addstr.assert_any_call(1, 1, text, curses.A_NORMAL)

    # More Comments
    comment_data = page.content.get(1)
    text = comment_data['body'].encode('utf-8')
    window.subwin.addstr.assert_any_call(0, 1, text, curses.A_NORMAL)

    # Cursor should not be drawn when the page is first opened
    assert not any(args[0][3] == curses.A_REVERSE
                   for args in window.subwin.addch.call_args_list)

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
        submission_page.selected_page = None
        terminal.prompt_input.return_value = 'front/top'
        submission_page.controller.trigger('/')

        submission_page.handle_selected_page()
        assert not submission_page.active
        assert submission_page.selected_page

        # Invalid input
        submission_page.active = True
        submission_page.selected_page = None
        terminal.prompt_input.return_value = 'front/pot'
        submission_page.controller.trigger('/')

        submission_page.handle_selected_page()
        assert submission_page.active
        assert not submission_page.selected_page


@pytest.mark.parametrize('prompt', PROMPTS.values(), ids=list(PROMPTS))
def test_submission_prompt_submission(submission_page, terminal, prompt):

    # Navigate to a different submission from inside a submission
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = prompt
        submission_page.content.order = 'top'
        submission_page.controller.trigger('/')
        assert not terminal.loader.exception

        submission_page.handle_selected_page()
        assert not submission_page.active
        assert submission_page.selected_page

        assert submission_page.selected_page.content.order is None
        data = submission_page.selected_page.content.get(-1)
        assert data['object'].id == '571dw3'


def test_submission_order(submission_page):

    submission_page.controller.trigger('1')
    assert submission_page.content.order == 'hot'
    submission_page.controller.trigger('2')
    assert submission_page.content.order == 'top'
    submission_page.controller.trigger('3')
    assert submission_page.content.order == 'rising'
    submission_page.controller.trigger('4')
    assert submission_page.content.order == 'new'
    submission_page.controller.trigger('5')
    assert submission_page.content.order == 'controversial'

    # Shouldn't be able to sort the submission page by gilded
    submission_page.controller.trigger('6')
    assert submission_page.content.order == 'controversial'


def test_submission_move_top_bottom(submission_page):

    submission_page.controller.trigger('G')
    assert submission_page.nav.absolute_index == 44

    submission_page.controller.trigger('g')
    submission_page.controller.trigger('g')
    assert submission_page.nav.absolute_index == -1


def test_submission_move_sibling_parent(submission_page):

    # Jump to sibling
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')
        submission_page.controller.trigger('J')
    assert submission_page.nav.absolute_index == 7

    # Jump to parent
    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('k')
        submission_page.controller.trigger('k')
        submission_page.controller.trigger('K')
    assert submission_page.nav.absolute_index == 0


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
    window.subwin.addstr.assert_any_call(6, 1, text, curses.A_NORMAL)


def test_submission_vote(submission_page, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Test voting on the submission
    with mock.patch('rtv.packages.praw.objects.Submission.upvote') as upvote,            \
            mock.patch('rtv.packages.praw.objects.Submission.downvote') as downvote,     \
            mock.patch('rtv.packages.praw.objects.Submission.clear_vote') as clear_vote:

        data = submission_page.get_selected_item()
        data['object'].archived = False

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


def test_submission_vote_archived(submission_page, refresh_token, terminal):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Load an archived submission
    archived_url = 'https://www.reddit.com/r/IAmA/comments/z1c9z/'
    submission_page.refresh_content(name=archived_url)

    with mock.patch.object(terminal, 'show_notification') as show_notification:
        data = submission_page.get_selected_item()

        # Upvote the submission
        show_notification.reset_mock()
        submission_page.controller.trigger('a')
        show_notification.assert_called_with('Voting disabled for archived post', style='Error')
        assert data['likes'] is None

        # Downvote the submission
        show_notification.reset_mock()
        submission_page.controller.trigger('z')
        show_notification.assert_called_with('Voting disabled for archived post', style='Error')
        assert data['likes'] is None


def test_submission_save(submission_page, refresh_token):

    # Log in
    submission_page.config.refresh_token = refresh_token
    submission_page.oauth.authorize()

    # Test save on the submission
    with mock.patch('rtv.packages.praw.objects.Submission.save') as save,        \
            mock.patch('rtv.packages.praw.objects.Submission.unsave') as unsave:

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

    # Test save on the comment submission
    with mock.patch('rtv.packages.praw.objects.Comment.save') as save,        \
            mock.patch('rtv.packages.praw.objects.Comment.unsave') as unsave:

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
    with mock.patch('rtv.packages.praw.objects.Submission.add_comment') as add_comment, \
            mock.patch.object(terminal, 'open_editor') as open_editor,                  \
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
    with mock.patch('rtv.packages.praw.objects.Comment.delete') as delete,  \
            mock.patch.object(terminal.stdscr, 'getch') as getch,           \
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
    with mock.patch('rtv.packages.praw.objects.Submission.edit') as edit,  \
            mock.patch.object(terminal, 'open_editor') as open_editor,     \
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
    with mock.patch('rtv.packages.praw.objects.Comment.edit') as edit, \
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


def test_submission_prompt_and_select_link(submission_page, terminal):

    # A link submission should return the URL that it's pointing to
    link = submission_page.prompt_and_select_link()
    assert link == 'https://github.com/michael-lazar/rtv'

    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')

    # The first comment doesn't have any links in the comment body
    link = submission_page.prompt_and_select_link()
    data = submission_page.get_selected_item()
    assert link == data['permalink']

    with mock.patch.object(submission_page, 'clear_input_queue'):
        submission_page.controller.trigger('j')

    # The second comment has a link embedded in the comment body, and
    # the user is prompted to select which link to open
    with mock.patch.object(terminal, 'prompt_user_to_select_link') as prompt:
        prompt.return_value = 'https://selected_link'

        link = submission_page.prompt_and_select_link()
        data = submission_page.get_selected_item()

        assert link == prompt.return_value

        embedded_url = 'http://peterdowns.com/posts/first-time-with-pypi.html'
        assert prompt.call_args[0][0] == [
            {'text': 'Permalink', 'href': data['permalink']},
            {'text': 'Relevant tutorial', 'href': embedded_url}
        ]

    submission_page.controller.trigger(' ')

    # The comment is now hidden so there are no links to select
    link = submission_page.prompt_and_select_link()
    assert link is None

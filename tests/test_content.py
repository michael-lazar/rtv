# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
from itertools import islice

import six
import praw
import pytest

from rtv.content import (
    Content, SubmissionContent, SubredditContent, SubscriptionContent)
from rtv import exceptions


def test_content_humanize_timestamp():

    timestamp = time.time() - 30
    assert Content.humanize_timestamp(timestamp) == '0min'
    assert Content.humanize_timestamp(timestamp, True) == 'moments ago'

    timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12
    assert Content.humanize_timestamp(timestamp) == '11month'
    assert Content.humanize_timestamp(timestamp, True) == '11 months ago'

    timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12 * 5
    assert Content.humanize_timestamp(timestamp) == '5yr'
    assert Content.humanize_timestamp(timestamp, True) == '5 years ago'


def test_content_wrap_text():

    text = 'four score\nand seven\n\n'
    assert Content.wrap_text(text, 6) == ['four', 'score', 'and', 'seven', '']
    assert Content.wrap_text(text, 15) == ['four score', 'and seven', '']
    assert Content.wrap_text('', 70) == []
    assert Content.wrap_text('\n\n\n\n', 70) == ['', '', '', '']


def test_content_flatten_comments(reddit):

    # Grab a large MoreComments instance to test
    url = 'https://www.reddit.com/r/AskReddit/comments/cmwov'
    submission = reddit.get_submission(url, comment_sort='top')
    more_comment = submission.comments[-1]
    assert isinstance(more_comment, praw.objects.MoreComments)

    # Double check that reddit's api hasn't changed the response structure
    comments = more_comment.comments()
    top_level_comments = []
    for comment in comments[:-1]:
        if comment.parent_id == more_comment.parent_id:
            top_level_comments.append(comment.id)
        else:
            # Sometimes replies are returned below their parents instead of
            # being automatically nested. In this case, make sure the parent_id
            # of the comment matches the most recent top level comment.
            assert comment.parent_id.endswith(top_level_comments[-1])

    # The last item should be a MoreComments linked to the original parent
    top_level_comments.append(comments[-1].id)
    assert isinstance(comments[-1], praw.objects.MoreComments)
    assert comments[-1].parent_id == more_comment.parent_id

    flattened = Content.flatten_comments(comments, root_level=2)

    # Because the comments returned by praw's comment.comments() don't have
    # nested replies, the flattened size should not change.
    assert len(flattened) == len(comments)
    for i, comment in enumerate(flattened):
        # Order should be preserved
        assert comment.id == comments[i].id
        # And the nested level should be added
        if comment.id in top_level_comments:
            assert comment.nested_level == 2
        else:
            assert comment.nested_level > 2


def test_content_submission_initialize(reddit, terminal):

    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader, indent_size=3,
                                max_indent_level=4, order='top')
    assert content.indent_size == 3
    assert content.max_indent_level == 4
    assert content.order == 'top'
    assert content.name is not None


def test_content_submission(reddit, terminal):

    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader)

    # Everything is loaded upon instantiation
    assert len(content._comment_data) == 45
    assert content.get(-1)['type'] == 'Submission'
    assert content.get(40)['type'] == 'Comment'

    for data in content.iterate(-1, 1):
        assert all(k in data for k in ('object', 'n_rows', 'offset', 'type',
                                       'hidden'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)

    # Out of bounds
    with pytest.raises(IndexError):
        content.get(-2)
    with pytest.raises(IndexError):
        content.get(50)

    # Toggling the submission doesn't do anything
    content.toggle(-1)
    assert len(content._comment_data) == 45

    # Toggling a comment hides its 3 children
    content.toggle(2)
    data = content.get(2)
    assert data['type'] == 'HiddenComment'
    assert data['count'] == 3
    assert data['hidden'] is True
    assert data['level'] >= content.get(3)['level']
    assert len(content._comment_data) == 43

    # Toggling again expands the children
    content.toggle(2)
    data = content.get(2)
    assert data['hidden'] is False
    assert len(content._comment_data) == 45


def test_content_submission_load_more_comments(reddit, terminal):

    url = 'https://www.reddit.com/r/AskReddit/comments/2np694/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader)
    assert len(content._comment_data) == 391

    # More comments load when toggled
    assert content.get(390)['type'] == 'MoreComments'
    content.toggle(390)
    assert len(content._comment_data) > 390
    assert content.get(390)['type'] == 'Comment'


def test_content_submission_from_url(reddit, oauth, refresh_token, terminal):

    url = 'https://www.reddit.com/r/AskReddit/comments/2np694/'
    SubmissionContent.from_url(reddit, url, terminal.loader)
    SubmissionContent.from_url(reddit, url, terminal.loader, order='new')

    # Invalid sorting order doesn't raise an exception
    with terminal.loader():
        SubmissionContent.from_url(reddit, url, terminal.loader, order='fake')
    assert not terminal.loader.exception

    # Invalid comment URL
    with terminal.loader():
        SubmissionContent.from_url(reddit, url[:-2], terminal.loader)
    assert isinstance(terminal.loader.exception, praw.errors.NotFound)

    # np.* urls should not raise a 403 error when logged into oauth
    oauth.config.refresh_token = refresh_token
    oauth.authorize()
    url = 'https://np.reddit.com//r/LifeProTips/comments/441hsf//czmp112.json'
    with terminal.loader():
        SubmissionContent.from_url(reddit, url, terminal.loader)
    assert not terminal.loader.exception


def test_content_subreddit_initialize(reddit, terminal):

    submissions = reddit.get_subreddit('python').get_top(limit=None)
    content = SubredditContent('python', submissions, terminal.loader, 'top')
    assert content.name == 'python'
    assert content.order == 'top'
    assert len(content._submission_data) == 1


def test_content_subreddit_initialize_invalid(reddit, terminal):

    submissions = reddit.get_subreddit('invalidsubreddit7').get_top(limit=None)
    with terminal.loader():
        SubredditContent('python', submissions, terminal.loader, 'top')
    assert isinstance(terminal.loader.exception, praw.errors.InvalidSubreddit)


def test_content_subreddit(reddit, terminal):

    submissions = reddit.get_front_page(limit=5)
    content = SubredditContent('front', submissions, terminal.loader)

    # Submissions are loaded on demand, excluding for the first one
    assert len(content._submission_data) == 1
    assert content.get(0)['type'] == 'Submission'

    for data in content.iterate(0, 1):
        assert all(k in data for k in (
            'object', 'n_rows', 'offset', 'type', 'index', 'title',
            'split_title', 'hidden'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)

    # Out of bounds
    with pytest.raises(IndexError):
        content.get(-1)
    with pytest.raises(IndexError):
        content.get(5)


def test_content_subreddit_load_more(reddit, terminal):

    submissions = reddit.get_front_page(limit=None)
    content = SubredditContent('front', submissions, terminal.loader)

    assert content.get(50)['type'] == 'Submission'
    assert len(content._submission_data) == 51

    for i, data in enumerate(islice(content.iterate(0, 1), 0, 50)):
        assert all(k in data for k in ('object', 'n_rows', 'offset', 'type',
                                       'index', 'title', 'split_title'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)

        # Index be appended to each title, starting at "1." and incrementing
        assert data['index'] == i + 1
        assert data['title'].startswith(six.text_type(i + 1))


def test_content_subreddit_from_name(reddit, terminal):

    name = '/r/python'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    assert content.name == '/r/python'
    assert content.order is None

    # Can submit without the /r/ and with the order in the name
    name = 'python/top/'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    assert content.name == '/r/python'
    assert content.order == 'top'

    # Explicit order trumps implicit
    name = '/r/python/top'
    content = SubredditContent.from_name(
        reddit, name, terminal.loader, order='new')
    assert content.name == '/r/python'
    assert content.order == 'new'

    # Invalid order raises an exception
    name = '/r/python/fake'
    with terminal.loader():
        SubredditContent.from_name(reddit, name, terminal.loader)
    assert isinstance(terminal.loader.exception, exceptions.SubredditError)

    # Front page alias
    name = '/r/front/rising'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    assert content.name == '/r/front'
    assert content.order == 'rising'

    # Queries
    SubredditContent.from_name(reddit, 'front', terminal.loader, query='pea')
    SubredditContent.from_name(reddit, 'python', terminal.loader, query='pea')


def test_content_subreddit_multireddit(reddit, terminal):

    name = '/r/python+linux'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    assert content.name == '/r/python+linux'

    # Invalid multireddit
    name = '/r/a+b'
    with terminal.loader():
        SubredditContent.from_name(reddit, name, terminal.loader)
    assert isinstance(terminal.loader.exception, praw.errors.NotFound)


def test_content_subreddit_random(reddit, terminal):

    name = '/r/random'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    assert content.name.startswith('/r/')
    assert content.name != name


def test_content_subreddit_me(reddit, oauth, refresh_token, terminal):

    # Not logged in
    with terminal.loader():
        SubredditContent.from_name(reddit, '/r/me', terminal.loader)
    assert isinstance(terminal.loader.exception, exceptions.AccountError)

    # Logged in
    oauth.config.refresh_token = refresh_token
    oauth.authorize()
    with terminal.loader():
        SubredditContent.from_name(reddit, 'me', terminal.loader)

    # If there is no submitted content, an error should be raised
    if terminal.loader.exception:
        assert isinstance(terminal.loader.exception, exceptions.SubredditError)


def test_content_subscription(reddit, oauth, refresh_token, terminal):

    # Not logged in
    with terminal.loader():
        SubscriptionContent.from_user(reddit, terminal.loader)
    assert isinstance(
        terminal.loader.exception, praw.errors.LoginOrScopeRequired)

    # Logged in
    oauth.config.refresh_token = refresh_token
    oauth.authorize()
    with terminal.loader():
        content = SubscriptionContent.from_user(reddit, terminal.loader)
    assert terminal.loader.exception is None

    # These are static
    assert content.name == 'Subscriptions'
    assert content.order is None

    # Validate content
    for data in content.iterate(0, 1, 70):
        assert all(k in data for k in ('object', 'n_rows', 'offset', 'type',
                                       'title', 'split_title'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)


def test_content_subscription_empty(terminal):

    # Simulate an empty subscription generator
    subscriptions = iter([])

    with terminal.loader():
        SubscriptionContent(subscriptions, terminal.loader)
    assert isinstance(terminal.loader.exception, exceptions.SubscriptionError)
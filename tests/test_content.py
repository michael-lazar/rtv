# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
from itertools import islice
from collections import OrderedDict

import six
import pytest

from rtv import exceptions
from rtv.packages import praw
from rtv.content import (
    Content, SubmissionContent, SubredditContent, SubscriptionContent,
    RequestHeaderRateLimiter)

try:
    from unittest import mock
except ImportError:
    import mock

# Test entering a bunch of text into the prompt
# (text, parsed subreddit, parsed order)
SUBREDDIT_PROMPTS = OrderedDict([
    ('plain-0', ('python', '/r/python', None)),
    ('plain-1', ('python/', '/r/python', None)),
    ('plain-2', ('r/python', '/r/python', None)),
    ('plain-3', ('/r/python', '/r/python', None)),
    ('new', ('/r/pics/new', '/r/pics', 'new')),
    ('hot', ('/r/pics/hot/', '/r/pics', 'hot')),
    ('top', ('pics/top', '/r/pics', 'top')),
    ('rising', ('r/pics/rising', '/r/pics', 'rising')),
    ('controversial', ('/r/pics/controversial', '/r/pics', 'controversial')),
    ('gilded', ('/r/pics/gilded', '/r/pics', 'gilded')),
    ('top-day', ('/r/pics/top-day', '/r/pics', 'top-day')),
    ('top-hour', ('/r/pics/top-hour', '/r/pics', 'top-hour')),
    ('top-month', ('/r/pics/top-month', '/r/pics', 'top-month')),
    ('top-week', ('/r/pics/top-week', '/r/pics', 'top-week')),
    ('top-year', ('/r/pics/top-year', '/r/pics', 'top-year')),
    ('top-all', ('/r/pics/top-all', '/r/pics', 'top-all')),
    ('pics_linux', ('/r/pics+linux', '/r/pics+linux', None)),
    ('multi-new', ('/r/pics+linux/new', '/r/pics+linux', 'new')),
    ('front_0', ('front', '/r/front', None)),
    ('front-1', ('/r/front', '/r/front', None)),
    ('front-new', ('/r/front/new', '/r/front', 'new')),
    ('front-top-week', ('/r/front/top-week', '/r/front', 'top-week')),
    ('user-0', ('/user/spez', '/u/spez', None)),
    ('user-1', ('/u/spez', '/u/spez', None)),
    ('user-new', ('/u/spez/new', '/u/spez', 'new')),
    ('user-top-all', ('/u/spez/top-all', '/u/spez', 'top-all')),
    ('user-overview', ('/u/spez/overview', '/u/spez/overview', None)),
    ('user-submitted', ('/u/spez/submitted', '/u/spez/submitted', None)),
    ('user-comments', ('/u/spez/comments', '/u/spez/comments', None)),
    ('multi-0', ('/user/multi-mod/m/art', '/u/multi-mod/m/art', None)),
    ('multi-1', ('/u/multi-mod/m/art', '/u/multi-mod/m/art', None)),
    ('multi-top', ('/u/multi-mod/m/art/top', '/u/multi-mod/m/art', 'top')),
    ('multi-top-all', ('/u/multi-mod/m/art/top-all', '/u/multi-mod/m/art', 'top-all')),
    ('domain', ('/domain/python.org', '/domain/python.org', None)),
    ('domain-new', ('/domain/python.org/new', '/domain/python.org', 'new')),
    ('domain-top-all', ('/domain/python.org/top-all', '/domain/python.org', 'top-all')),
])

# Will raise an error if not logged in
SUBREDDIT_AUTH_PROMPTS = OrderedDict([
    ('me-0', ('/user/me', '/u/me', None)),
    ('me-1', ('/u/me', '/u/me', None)),
    ('me-top', ('/u/me/top', '/u/me', 'top')),
    ('me-top-all', ('/u/me/top-all', '/u/me', 'top-all')),
    ('me-saved', ('/u/me/saved', '/u/me/saved', None)),
    ('me-upvoted', ('/u/me/upvoted', '/u/me/upvoted', None)),
    ('me-downvoted', ('/u/me/downvoted', '/u/me/downvoted', None)),
    ('me-hidden', ('/u/me/hidden', '/u/me/hidden', None)),
    ('me-multi', ('/u/me/m/redditpets/top-all', '/u/{username}/m/redditpets', 'top-all')),
])

# All of these should raise an error when entered
SUBREDDIT_INVALID_PROMPTS = OrderedDict([
    ('empty', ''),
    ('one-slash', '/'),
    ('two-slashes', '//'),
    ('many-slashes', '/////////////////'),
    ('fake', '/r/python/fake'),
    ('top-fake', '/r/python/top-fake'),
    ('new-all', '/r/python/new-all'),
])

# All of these search queries should return at least some submissions
# (subreddit, search query)
SUBREDDIT_SEARCH_QUERIES = OrderedDict([
    # https://github.com/reddit/reddit/issues/1816
    ('front', ('/r/front', 'reddit2')),
    ('python', ('/r/python', 'python')),
    ('python-top', ('/r/python/top-all', 'guido')),
    ('user', ('/u/spez', 'ama')),
    ('user-top', ('/user/spez/top-all', 'ama')),
    ('multi', ('/u/multi-mod/m/art', 'PsBattle')),
    ('multi-top', ('/u/multi-mod/m/art/top-all', 'PsBattle')),
    ('domain', ('/domain/python.org', 'Python')),
    ('domain-top', ('/domain/python.org/top-all', 'Python')),
])


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


@pytest.mark.skip('Reddit API changed, need to update this test')
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
            if not comment.parent_id.endswith(top_level_comments[-1]):
                pass

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


def test_content_flatten_comments_2(reddit):

    # Grab a large MoreComments instance to test
    url = 'https://www.reddit.com/r/CollegeBasketball/comments/31owr1'
    submission = reddit.get_submission(url, comment_sort='top')
    more_comment = submission.comments[-1]
    assert isinstance(more_comment, praw.objects.MoreComments)

    # Make sure that all comments are displayed one level below their parents
    comments = more_comment.comments()
    flattened = Content.flatten_comments(comments)
    for i, item in enumerate(flattened):
        for j in range(i-1, -1, -1):
            prev = flattened[j]
            if item.parent_id and item.parent_id.endswith(prev.id):
                x, y = item.nested_level, prev.nested_level
                assert item.nested_level == prev.nested_level + 1
                break
        else:
            assert item.nested_level == 0


def test_content_flatten_comments_3(reddit):
    # Build the comment structure as described in issue
    # https://github.com/michael-lazar/rtv/issues/327

    class MockComment(object):
        def __init__(self, comment_id, parent_id='t3_xxxxx'):
            self.id = comment_id
            self.parent_id = parent_id
            self.replies = []

        def __repr__(self):
            return '%s (%s)' % (self.id, self.parent_id)

    # This is an example of something that might be returned by PRAW after
    # clicking to expand a "More comments [6]" link.
    comments = [
        MockComment('axxxx'),
        MockComment('a1xxx', parent_id='t1_axxxx'),
        MockComment('a11xx', parent_id='t1_a1xxx'),
        MockComment('a12xx', parent_id='t1_a1xxx'),
        MockComment('a2xxx', parent_id='t1_axxxx'),
        MockComment('a3xxx', parent_id='t1_axxxx'),
        MockComment('bxxxx'),
    ]

    # Make sure that all comments are displayed one level below their parents
    flattened = Content.flatten_comments(comments)
    for i, item in enumerate(flattened):
        for j in range(i-1, -1, -1):
            prev = flattened[j]
            if item.parent_id and item.parent_id.endswith(prev.id):
                x, y = item.nested_level, prev.nested_level
                assert item.nested_level == prev.nested_level + 1
                break
        else:
            assert item.nested_level == 0


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
    assert content.range == (-1, 44)
    assert content.get(-1)['type'] == 'Submission'
    assert content.get(40)['type'] == 'Comment'

    for data in content.iterate(-1, 1):
        assert all(k in data for k in ('object', 'n_rows', 'h_offset', 'type',
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
    assert content.range == (-1, 42)

    # Toggling again expands the children
    content.toggle(2)
    data = content.get(2)
    assert data['hidden'] is False
    assert content.range == (-1, 44)


def test_content_submission_load_more_comments(reddit, terminal):

    url = 'https://www.reddit.com/r/AskReddit/comments/2np694/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader)
    last_index = len(content._comment_data) - 1

    # More comments load when toggled
    assert content.get(last_index)['type'] == 'MoreComments'
    content.toggle(last_index)

    # Loading more comments should increase the range
    assert content.range[0] == -1
    assert content.range[1] > last_index
    assert content.get(last_index)['type'] == 'Comment'


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
    assert content.range == (0, 0)


def test_content_subreddit_initialize_invalid(reddit, terminal):

    submissions = reddit.get_subreddit('invalidsubreddit7').get_top(limit=None)
    with terminal.loader():
        SubredditContent('python', submissions, terminal.loader, 'top')
    assert isinstance(terminal.loader.exception, praw.errors.InvalidSubreddit)


def test_content_subreddit(reddit, terminal):

    submissions = reddit.get_front_page(limit=5)
    content = SubredditContent('front', submissions, terminal.loader)

    # Submissions are loaded on demand, excluding for the first one
    assert content.range == (0, 0)
    assert content.get(0)['type'] == 'Submission'

    for data in content.iterate(0, 1):
        assert all(k in data for k in (
            'object', 'n_rows', 'h_offset', 'type', 'index', 'title',
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
    assert content.range == (0, 50)

    for i, data in enumerate(islice(content.iterate(0, 1), 0, 50)):
        assert all(k in data for k in ('object', 'n_rows', 'h_offset', 'type',
                                       'index', 'title', 'split_title'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)

        # Index be appended to each title, starting at "1." and incrementing
        assert data['index'] == i + 1
        assert data['title'].startswith(six.text_type(i + 1))


args, ids = SUBREDDIT_PROMPTS.values(), list(SUBREDDIT_PROMPTS)
@pytest.mark.parametrize('prompt,name,order', args, ids=ids)
def test_content_subreddit_from_name(prompt, name, order, reddit, terminal):

    content = SubredditContent.from_name(reddit, prompt, terminal.loader)
    assert content.name == name
    assert content.order == order


args, ids = SUBREDDIT_AUTH_PROMPTS.values(), list(SUBREDDIT_AUTH_PROMPTS)
@pytest.mark.parametrize('prompt,name,order', args, ids=ids)
def test_content_subreddit_from_name_authenticated(
        prompt, name, order, reddit, terminal, oauth, refresh_token):

    with pytest.raises(exceptions.AccountError):
        SubredditContent.from_name(reddit, prompt, terminal.loader)

    # Login and try again
    oauth.config.refresh_token = refresh_token
    oauth.authorize()

    if '{username}' in name:
        name = name.format(username=reddit.user.name)

    content = SubredditContent.from_name(reddit, prompt, terminal.loader)
    assert content.name == name
    assert content.order == order


args, ids = SUBREDDIT_INVALID_PROMPTS.values(), list(SUBREDDIT_INVALID_PROMPTS)
@pytest.mark.parametrize('prompt', args, ids=ids)
def test_content_subreddit_from_name_invalid(prompt, reddit, terminal):

    with terminal.loader():
        SubredditContent.from_name(reddit, prompt, terminal.loader)
    assert isinstance(terminal.loader.exception, praw.errors.InvalidSubreddit)
    # Must always have an argument because it gets displayed
    assert terminal.loader.exception.args[0]


args, ids = SUBREDDIT_SEARCH_QUERIES.values(), list(SUBREDDIT_SEARCH_QUERIES)
@pytest.mark.parametrize('prompt,query', args, ids=ids)
def test_content_subreddit_from_name_query(prompt, query, reddit, terminal):

    SubredditContent.from_name(reddit, prompt, terminal.loader, query=query)


def test_content_subreddit_from_name_order(reddit, terminal):

    # Explicit order trumps implicit
    name = '/r/python/top'
    content = SubredditContent.from_name(
        reddit, name, terminal.loader, order='new')
    assert content.name == '/r/python'
    assert content.order == 'new'


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


def test_content_subreddit_gilded(reddit, terminal):

    name = '/r/python/gilded'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    assert content.order == 'gilded'
    assert content.get(0)['object'].gilded


def test_content_subreddit_me(reddit, oauth, refresh_token, terminal):

    # Not logged in
    with terminal.loader():
        SubredditContent.from_name(reddit, '/u/me', terminal.loader)
    assert isinstance(terminal.loader.exception, exceptions.AccountError)

    # Logged in
    oauth.config.refresh_token = refresh_token
    oauth.authorize()
    with terminal.loader():
        SubredditContent.from_name(reddit, '/u/me', terminal.loader)

    # If there is no submitted content, an error should be raised
    if terminal.loader.exception:
        assert isinstance(terminal.loader.exception,
                          exceptions.NoSubmissionsError)
        assert terminal.loader.exception.name == '/u/me'

def test_content_subreddit_nsfw_filter(reddit, oauth, refresh_token, terminal):

    # NSFW subreddits should load if not logged in
    name = '/r/ImGoingToHellForThis'
    SubredditContent.from_name(reddit, name, terminal.loader)

    # Log in
    oauth.config.refresh_token = refresh_token
    oauth.authorize()

    # Make sure the API parameter hasn't changed
    assert reddit.user.over_18 is not None

    # Turn on safe search
    reddit.user.over_18 = False

    # Should refuse to load this subreddit
    with pytest.raises(exceptions.SubredditError):
        name = '/r/ImGoingToHellForThis'
        SubredditContent.from_name(reddit, name, terminal.loader)

    # Should filter out all of the nsfw posts
    name = '/r/ImGoingToHellForThis+python'
    content = SubredditContent.from_name(reddit, name, terminal.loader)
    for data in islice(content.iterate(0, 1), 50):
        assert data['object'].over_18 is False

    # Turn off safe search
    reddit.user.over_18 = True

    # The NSFW subreddit should load now
    name = '/r/ImGoingToHellForThis'
    SubredditContent.from_name(reddit, name, terminal.loader)


def test_content_subscription(reddit, terminal):

    # Not logged in
    with terminal.loader():
        SubscriptionContent.from_user(reddit, terminal.loader)
    assert isinstance(
        terminal.loader.exception, praw.errors.LoginOrScopeRequired)

    with terminal.loader():
        content = SubscriptionContent.from_user(
            reddit, terminal.loader, 'popular')
    assert terminal.loader.exception is None

    # These are static
    assert content.name == 'Popular Subreddits'
    assert content.order is None
    assert content.range == (0, 0)

    # Validate content
    for data in islice(content.iterate(0, 1), 20):
        assert all(k in data for k in ('object', 'n_rows', 'h_offset', 'type',
                                       'title', 'split_title'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)

    assert content.range == (0, 19)


def test_content_subreddit_saved(reddit, oauth, refresh_token, terminal):

    # Not logged in
    with terminal.loader():
        SubredditContent.from_name(reddit, '/u/me/saved', terminal.loader)
    assert isinstance(terminal.loader.exception, exceptions.AccountError)

    # Logged in
    oauth.config.refresh_token = refresh_token
    oauth.authorize()
    with terminal.loader():
        SubredditContent.from_name(reddit, '/u/me/saved', terminal.loader)


def test_content_subscription_empty(reddit, terminal):

    # Simulate an empty subscription list
    with mock.patch.object(reddit, 'get_my_subreddits') as func:
        func.return_value = iter([])
        with terminal.loader():
            SubscriptionContent.from_user(reddit, terminal.loader)
    assert isinstance(terminal.loader.exception, exceptions.SubscriptionError)


def test_content_cache(reddit):

    # Make sure the test suite is configured to use the custom handler
    assert isinstance(reddit.handler, RequestHeaderRateLimiter)
    assert not reddit.handler.cache

    # A standard 200 response should be added to the cache
    next(reddit.get_subreddit('python').get_hot())
    request = list(reddit.handler.cache.values())[0]
    assert request.url == 'https://api.reddit.com/r/python/.json'

    # Clearing the cache should remove the request
    reddit.handler.cache.clear()
    assert not reddit.handler.cache

    next(reddit.get_subreddit('python').get_hot())
    assert reddit.handler.cache

    # Evicting the cache should also remove the entry
    reddit.handler.evict('https://api.reddit.com/r/python')
    assert not reddit.handler.cache


def test_content_rate_limit(reddit, oauth, refresh_token):

    # Make sure the test suite is configured to use the custom handler
    assert isinstance(reddit.handler, RequestHeaderRateLimiter)
    assert not reddit.handler.cache

    # unauthenticated requests don't return the x-ratelimit headers
    # so they currently aren't limited
    next(reddit.get_subreddit('python').get_hot())
    assert reddit.handler.seconds_to_reset is None

    oauth.config.refresh_token = refresh_token
    oauth.authorize()

    # But now that we're logged in the headers should be returned
    next(reddit.get_subreddit('python').get_hot())
    assert reddit.handler.seconds_to_reset

    # Even though the headers were returned, the rate limiting should
    # still not be triggering a delay for the next request
    assert reddit.handler.next_request_timestamp is None


def test_content_extract_links():

    # Should handle relative & absolute links, should ignore empty links.
    html = """
    <a href='/'>Home Page</a>
    <a href='https://www.github.com'>Github</a>
    <a>Blank</a>
    """
    assert Content.extract_links(html) == [
        {'href': 'https://www.reddit.com/', 'text': 'Home Page'},
        {'href': 'https://www.github.com', 'text': 'Github'}
    ]

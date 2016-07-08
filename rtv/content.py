# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from datetime import datetime

import six
import praw
from praw.errors import InvalidSubreddit
from kitchen.text.display import wrap

from . import exceptions


class Content(object):

    def get(self, index, n_cols):
        raise NotImplementedError

    def iterate(self, index, step, n_cols=70):

        while True:
            if step < 0 and index < 0:
                # Hack to prevent displaying a submission's post if iterating
                # comments in the negative direction
                break
            try:
                yield self.get(index, n_cols=n_cols)
            except IndexError:
                break
            index += step

    @staticmethod
    def flatten_comments(comments, root_level=0):
        """
        Flatten a PRAW comment tree while preserving the nested level of each
        comment via the `nested_level` attribute.
        """

        stack = comments[:]
        for item in stack:
            item.nested_level = root_level

        retval = []
        while stack:
            item = stack.pop(0)

            # MoreComments item count should never be zero, but if it is then
            # discard the MoreComment object. Need to look into this further.
            if isinstance(item, praw.objects.MoreComments) and item.count == 0:
                continue

            # https://github.com/praw-dev/praw/issues/391
            # Attach children replies to parents. Children will have the
            # same parent_id, but with a suffix attached.
            # E.g.
            #   parent_comment.id = c0tprcm
            #   comment.parent_id = t1_c0tprcm
            if item.parent_id:
                level = None
                # Search through previous comments for a possible parent
                for parent in retval[::-1]:
                    if level and parent.nested_level >= level:
                        # Stop if we reach a sibling or a child, we know that
                        # nothing before this point is a candidate for parent.
                        break
                    level = parent.nested_level
                    if item.parent_id.endswith(parent.id):
                        item.nested_level = parent.nested_level + 1

            # Otherwise, grab all of the attached replies and add them back to
            # the list of comments to parse
            if hasattr(item, 'replies'):
                for n in item.replies:
                    n.nested_level = item.nested_level + 1
                stack[0:0] = item.replies

            retval.append(item)
        return retval

    @classmethod
    def strip_praw_comment(cls, comment):
        """
        Parse through a submission comment and return a dict with data ready to
        be displayed through the terminal.
        """

        data = {}
        data['object'] = comment
        data['level'] = comment.nested_level

        if isinstance(comment, praw.objects.MoreComments):
            data['type'] = 'MoreComments'
            data['count'] = comment.count
            data['body'] = 'More comments'
            data['hidden'] = True
        else:
            author = getattr(comment, 'author', '[deleted]')
            name = getattr(author, 'name', '[deleted]')
            sub = getattr(comment, 'submission', '[deleted]')
            sub_author = getattr(sub, 'author', '[deleted]')
            sub_name = getattr(sub_author, 'name', '[deleted]')
            flair = getattr(comment, 'author_flair_text', '')
            permalink = getattr(comment, 'permalink', None)
            stickied = getattr(comment, 'stickied', False)

            data['type'] = 'Comment'
            data['body'] = comment.body
            data['created'] = cls.humanize_timestamp(comment.created_utc)
            data['score'] = '{0} pts'.format(
                '-' if comment.score_hidden else comment.score)
            data['author'] = name
            data['is_author'] = (name == sub_name)
            data['flair'] = flair
            data['likes'] = comment.likes
            data['gold'] = comment.gilded > 0
            data['permalink'] = permalink
            data['stickied'] = stickied
            data['hidden'] = False

        return data

    @classmethod
    def strip_praw_submission(cls, sub):
        """
        Parse through a submission and return a dict with data ready to be
        displayed through the terminal.

        Definitions:
            permalink - URL to the reddit page with submission comments.
            url_full - URL that the submission points to.
            url - URL that will be displayed on the subreddit page, may be
                "selfpost", "x-post submission", "x-post subreddit", or an
                external link.
        """

        reddit_link = re.compile(
            r'https?://(www\.)?(np\.)?redd(it\.com|\.it)/r/.*')
        author = getattr(sub, 'author', '[deleted]')
        name = getattr(author, 'name', '[deleted]')
        flair = getattr(sub, 'link_flair_text', '')

        data = {}
        data['object'] = sub
        data['type'] = 'Submission'
        data['title'] = sub.title
        data['text'] = sub.selftext
        data['created'] = cls.humanize_timestamp(sub.created_utc)
        data['comments'] = '{0} comments'.format(sub.num_comments)
        data['score'] = '{0} pts'.format('-' if sub.hide_score else sub.score)
        data['author'] = name
        data['permalink'] = sub.permalink
        data['subreddit'] = six.text_type(sub.subreddit)
        data['flair'] = '[{0}]'.format(flair.strip(' []')) if flair else ''
        data['url_full'] = sub.url
        data['likes'] = sub.likes
        data['gold'] = sub.gilded > 0
        data['nsfw'] = sub.over_18
        data['stickied'] = sub.stickied
        data['hidden'] = False
        data['xpost_subreddit'] = None
        data['index'] = None  # This is filled in later by the method caller

        if sub.url.split('/r/')[-1] == sub.permalink.split('/r/')[-1]:
            data['url'] = 'self.{0}'.format(data['subreddit'])
            data['url_type'] = 'selfpost'
        elif reddit_link.match(sub.url):
            # Strip the subreddit name from the permalink to avoid having
            # submission.subreddit.url make a separate API call
            url_parts = sub.url.split('/')
            data['xpost_subreddit'] = url_parts[4]
            data['url'] = 'self.{0}'.format(url_parts[4])
            if 'comments' in url_parts:
                data['url_type'] = 'x-post submission'
            else:
                data['url_type'] = 'x-post subreddit'
        else:
            data['url'] = sub.url
            data['url_type'] = 'external'

        return data

    @staticmethod
    def strip_praw_subscription(subscription):
        """
        Parse through a subscription and return a dict with data ready to be
        displayed through the terminal.
        """

        data = {}
        data['object'] = subscription
        data['type'] = 'Subscription'
        data['name'] = "/r/" + subscription.display_name
        data['title'] = subscription.title
        return data

    @staticmethod
    def humanize_timestamp(utc_timestamp, verbose=False):
        """
        Convert a utc timestamp into a human readable relative-time.
        """

        timedelta = datetime.utcnow() - datetime.utcfromtimestamp(utc_timestamp)

        seconds = int(timedelta.total_seconds())
        if seconds < 60:
            return 'moments ago' if verbose else '0min'
        minutes = seconds // 60
        if minutes < 60:
            return '%d minutes ago' % minutes if verbose else '%dmin' % minutes
        hours = minutes // 60
        if hours < 24:
            return '%d hours ago' % hours if verbose else '%dhr' % hours
        days = hours // 24
        if days < 30:
            return '%d days ago' % days if verbose else '%dday' % days
        months = days // 30.4
        if months < 12:
            return '%d months ago' % months if verbose else '%dmonth' % months
        years = months // 12
        return '%d years ago' % years if verbose else '%dyr' % years

    @staticmethod
    def wrap_text(text, width):
        """
        Wrap text paragraphs to the given character width while preserving
        newlines.
        """
        out = []
        for paragraph in text.splitlines():
            # Wrap returns an empty list when paragraph is a newline. In order
            # to preserve newlines we substitute a list containing an empty
            # string.
            lines = wrap(paragraph, width=width) or ['']
            out.extend(lines)
        return out


class SubmissionContent(Content):
    """
    Grab a submission from PRAW and lazily store comments to an internal
    list for repeat access.
    """

    def __init__(self, submission, loader, indent_size=2, max_indent_level=8,
                 order=None):

        submission_data = self.strip_praw_submission(submission)
        comments = self.flatten_comments(submission.comments)

        self.indent_size = indent_size
        self.max_indent_level = max_indent_level
        self.name = submission_data['permalink']
        self.order = order
        self._loader = loader
        self._submission = submission
        self._submission_data = submission_data
        self._comment_data = [self.strip_praw_comment(c) for c in comments]

    @classmethod
    def from_url(cls, reddit, url, loader, indent_size=2, max_indent_level=8,
                 order=None):

        url = url.replace('http:', 'https:')  # Reddit forces SSL
        # Sometimes reddit will return a 403 FORBIDDEN when trying to access an
        # np link while using OAUTH. Cause is unknown.
        url = url.replace('https://np.', 'https://www.')
        submission = reddit.get_submission(url, comment_sort=order)
        return cls(submission, loader, indent_size, max_indent_level, order)

    def get(self, index, n_cols=70):
        """
        Grab the `i`th submission, with the title field formatted to fit inside
        of a window of width `n`
        """

        if index < -1:
            raise IndexError

        elif index == -1:
            data = self._submission_data
            data['split_title'] = self.wrap_text(data['title'], width=n_cols-2)
            data['split_text'] = self.wrap_text(data['text'], width=n_cols-2)
            data['n_rows'] = len(data['split_title'] + data['split_text']) + 5
            data['offset'] = 0

        else:
            data = self._comment_data[index]
            indent_level = min(data['level'], self.max_indent_level)
            data['offset'] = indent_level * self.indent_size

            if data['type'] == 'Comment':
                width = n_cols - data['offset']
                data['split_body'] = self.wrap_text(data['body'], width=width)
                data['n_rows'] = len(data['split_body']) + 1
            else:
                data['n_rows'] = 1

        return data

    def toggle(self, index, n_cols=70):
        """
        Toggle the state of the object at the given index.

        If it is a comment, pack it into a hidden comment.
        If it is a hidden comment, unpack it.
        If it is more comments, load the comments.
        """
        data = self.get(index)

        if data['type'] == 'Submission':
            # Can't hide the submission!
            pass

        elif data['type'] == 'Comment':
            cache = [data]
            count = 1
            for d in self.iterate(index + 1, 1, n_cols):
                if d['level'] <= data['level']:
                    break

                count += d.get('count', 1)
                cache.append(d)

            comment = {
                'type': 'HiddenComment',
                'cache': cache,
                'count': count,
                'level': data['level'],
                'body': 'Hidden',
                'hidden': True}

            self._comment_data[index:index + len(cache)] = [comment]

        elif data['type'] == 'HiddenComment':
            self._comment_data[index:index + 1] = data['cache']

        elif data['type'] == 'MoreComments':
            with self._loader('Loading comments'):
                # Undefined behavior if using a nested loader here
                assert self._loader.depth == 1
                comments = data['object'].comments(update=True)
            if not self._loader.exception:
                comments = self.flatten_comments(comments, data['level'])
                comment_data = [self.strip_praw_comment(c) for c in comments]
                self._comment_data[index:index + 1] = comment_data

        else:
            raise ValueError('%s type not recognized' % data['type'])


class SubredditContent(Content):
    """
    Grab a subreddit from PRAW and lazily stores submissions to an internal
    list for repeat access.
    """

    def __init__(self, name, submissions, loader, order=None):

        self.name = name
        self.order = order
        self._loader = loader
        self._submissions = submissions
        self._submission_data = []

        # Verify that content exists for the given submission generator.
        # This is necessary because PRAW loads submissions lazily, and
        # there is is no other way to check things like multireddits that
        # don't have a real corresponding subreddit object.
        try:
            self.get(0)
        except IndexError:
            raise exceptions.SubredditError('No submissions')

    @classmethod
    def from_name(cls, reddit, name, loader, order=None, query=None):

        # Strip leading and trailing backslashes
        name = name.strip(' /')
        if name.startswith('r/'):
            name = name[2:]

        # If the order is not given explicitly, it will be searched for and
        # stripped out of the subreddit name e.g. python/new.
        if '/' in name:
            name, name_order = name.split('/')
            order = order or name_order
        display_name = '/r/{0}'.format(name)

        if order not in ['hot', 'top', 'rising', 'new', 'controversial', None]:
            raise exceptions.SubredditError('Unrecognized order "%s"' % order)

        if name == 'me':
            if not reddit.is_oauth_session():
                raise exceptions.AccountError('Not logged in')
            elif order:
                submissions = reddit.user.get_submitted(sort=order)
            else:
                submissions = reddit.user.get_submitted()

        elif query:
            if name == 'front':
                submissions = reddit.search(query, subreddit=None, sort=order)
            else:
                submissions = reddit.search(query, subreddit=name, sort=order)

        else:
            if name == '':
                # Praw does not correctly handle empty strings
                # https://github.com/praw-dev/praw/issues/615
                raise InvalidSubreddit()

            if name == 'front':
                dispatch = {
                    None: reddit.get_front_page,
                    'hot': reddit.get_front_page,
                    'top': reddit.get_top,
                    'rising': reddit.get_rising,
                    'new': reddit.get_new,
                    'controversial': reddit.get_controversial,
                    }
            else:
                subreddit = reddit.get_subreddit(name)
                # For special subreddits like /r/random we want to replace the
                # display name with the one returned by the request.
                display_name = '/r/{0}'.format(subreddit.display_name)
                dispatch = {
                    None: subreddit.get_hot,
                    'hot': subreddit.get_hot,
                    'top': subreddit.get_top,
                    'rising': subreddit.get_rising,
                    'new': subreddit.get_new,
                    'controversial': subreddit.get_controversial,
                    }
            submissions = dispatch[order](limit=None)

        return cls(display_name, submissions, loader, order=order)

    def get(self, index, n_cols=70):
        """
        Grab the `i`th submission, with the title field formatted to fit inside
        of a window of width `n_cols`
        """

        if index < 0:
            raise IndexError

        while index >= len(self._submission_data):
            try:
                with self._loader('Loading more submissions'):
                    submission = next(self._submissions)
                if self._loader.exception:
                    raise IndexError
            except StopIteration:
                raise IndexError
            else:
                data = self.strip_praw_submission(submission)
                data['index'] = len(self._submission_data) + 1
                # Add the post number to the beginning of the title
                data['title'] = '{0}. {1}'.format(data['index'], data['title'])
                self._submission_data.append(data)

        # Modifies the original dict, faster than copying
        data = self._submission_data[index]
        data['split_title'] = self.wrap_text(data['title'], width=n_cols)
        data['n_rows'] = len(data['split_title']) + 3
        data['offset'] = 0

        return data


class SubscriptionContent(Content):

    def __init__(self, subscriptions, loader):

        self.name = "Subscriptions"
        self.order = None
        self._loader = loader
        self._subscriptions = subscriptions
        self._subscription_data = []

        try:
            self.get(0)
        except IndexError:
            raise exceptions.SubscriptionError('No subscriptions')

    @classmethod
    def from_user(cls, reddit, loader):
        subscriptions = reddit.get_my_subreddits(limit=None)
        return cls(subscriptions, loader)

    def get(self, index, n_cols=70):
        """
        Grab the `i`th subscription, with the title field formatted to fit
        inside of a window of width `n_cols`
        """

        if index < 0:
            raise IndexError

        while index >= len(self._subscription_data):
            try:
                with self._loader('Loading subscriptions'):
                    subscription = next(self._subscriptions)
                if self._loader.exception:
                    raise IndexError
            except StopIteration:
                raise IndexError
            else:
                data = self.strip_praw_subscription(subscription)
                self._subscription_data.append(data)

        data = self._subscription_data[index]
        data['split_title'] = self.wrap_text(data['title'], width=n_cols)
        data['n_rows'] = len(data['split_title']) + 1
        data['offset'] = 0

        return data

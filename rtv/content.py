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
        """
        Grab the item at the given index, and format the text to fit a width of
        n columns.
        """
        raise NotImplementedError

    def iterate(self, index, step, n_cols=70):
        """
        Return an iterator that starts and the current index and increments
        by the given step.
        """

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

    @property
    def range(self):
        """
        Return the minimm and maximum valid indicies.
        """
        raise NotImplementedError

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

        if isinstance(comment, praw.objects.MoreComments):
            data['type'] = 'MoreComments'
            data['level'] = comment.nested_level
            data['count'] = comment.count
            data['body'] = 'More comments'
            data['hidden'] = True

        elif hasattr(comment, 'nested_level'):
            author = getattr(comment, 'author', '[deleted]')
            name = getattr(author, 'name', '[deleted]')
            sub = getattr(comment, 'submission', '[deleted]')
            sub_author = getattr(sub, 'author', '[deleted]')
            sub_name = getattr(sub_author, 'name', '[deleted]')
            flair = getattr(comment, 'author_flair_text', '')
            permalink = getattr(comment, 'permalink', None)
            stickied = getattr(comment, 'stickied', False)

            data['type'] = 'Comment'
            data['level'] = comment.nested_level
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
            data['saved'] = comment.saved
        else:
            # Saved comments don't have a nested level and are missing a couple
            # of fields like ``submission``. As a result, we can only load a
            # subset of fields to avoid triggering a seperate api call to load
            # the full comment.
            author = getattr(comment, 'author', '[deleted]')
            stickied = getattr(comment, 'stickied', False)
            flair = getattr(comment, 'author_flair_text', '')

            data['type'] = 'SavedComment'
            data['level'] = None
            data['title'] = comment.body
            data['comments'] = ''
            data['url_full'] = comment._fast_permalink
            data['url'] = comment._fast_permalink
            data['nsfw'] = comment.over_18
            data['subreddit'] = six.text_type(comment.subreddit)
            data['url_type'] = 'selfpost'
            data['score'] = '{0} pts'.format(
                '-' if comment.score_hidden else comment.score)
            data['likes'] = comment.likes
            data['created'] = cls.humanize_timestamp(comment.created_utc)
            data['saved'] = comment.saved
            data['stickied'] = stickied
            data['gold'] = comment.gilded > 0
            data['author'] = author
            data['flair'] = flair

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
        data['saved'] = sub.saved

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
        if isinstance(subscription, praw.objects.Multireddit):
            data['type'] = 'Multireddit'
            data['name'] = subscription.path
            data['title'] = subscription.description_md
        else:
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
                 order=None, max_comment_cols=120):

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
        self._max_comment_cols = max_comment_cols

    @classmethod
    def from_url(cls, reddit, url, loader, indent_size=2, max_indent_level=8,
                 order=None, max_comment_cols=120):

        url = url.replace('http:', 'https:')  # Reddit forces SSL
        # Sometimes reddit will return a 403 FORBIDDEN when trying to access an
        # np link while using OAUTH. Cause is unknown.
        url = url.replace('https://np.', 'https://www.')
        submission = reddit.get_submission(url, comment_sort=order)
        return cls(submission, loader, indent_size, max_indent_level, order,
            max_comment_cols)

    @property
    def range(self):
        return -1, len(self._comment_data) - 1

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
                width = min(n_cols - data['offset'], self._max_comment_cols)
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

    def __init__(self, name, submissions, loader, order=None, max_title_rows=4):

        self.name = name
        self.order = order
        self.max_title_rows = max_title_rows
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
            full_name = self.name
            if self.order:
                full_name += '/' + self.order
            raise exceptions.NoSubmissionsError(full_name)

    @classmethod
    def from_name(cls, reddit, name, loader, order=None, query=None):
        """
        Params:
            reddit (praw.Reddit): Instance of the reddit api.
            name (text): The name of the desired subreddit, user, multireddit,
                etc. In most cases this translates directly from the URL that
                reddit itself uses. This is what users will type in the command
                prompt when they navigate to a new location.
            loader (terminal.loader): Handler for the load screen that will be
                displayed when making http requests.
            order (text): If specified, the order that posts will be sorted in.
                For `top` and `controversial`, you can specify the time frame
                by including a dash, e.g. "top-year". If an order is not
                specified, it will be extracted from the name.
            query (text): Content to search for on the given subreddit or
                user's page.
        """
        # TODO: refactor this into smaller methods

        # Strip leading, trailing, and redundant backslashes
        parts = [seg for seg in name.strip(' /').split('/') if seg]

        # Check for the resource type, assume /r/ as the default
        if len(parts) >= 3 and parts[2] == 'm':
            # E.g. /u/multi-mod/m/android
            resource_root, parts = '/'.join(parts[:3]), parts[3:]
        elif len(parts) > 1 and parts[0] in ['r', 'u', 'user', 'domain']:
            resource_root = parts.pop(0)
        else:
            resource_root = 'r'

        if resource_root == 'user':
            resource_root = 'u'

        # There should at most two parts left, the resource and the order
        if len(parts) == 1:
            resource, resource_order = parts[0], None
        elif len(parts) == 2:
            resource, resource_order = parts
        else:
            raise InvalidSubreddit('`{}` is an invalid format'.format(name))

        if not resource:
            # Praw does not correctly handle empty strings
            # https://github.com/praw-dev/praw/issues/615
            raise InvalidSubreddit('Subreddit cannot be empty')

        # If the order was explicitly passed in, it will take priority over
        # the order that was extracted from the name
        order = order or resource_order

        display_order = order
        display_name = '/'.join(['', resource_root, resource])

        # Split the order from the period E.g. controversial-all, top-hour
        if order and '-' in order:
            order, period = order.split('-', 1)
        else:
            period = None

        if order not in ['hot', 'top', 'rising', 'new', 'controversial', None]:
            raise InvalidSubreddit('Invalid order `%s`' % order)
        if period not in ['all', 'day', 'hour', 'month', 'week', 'year', None]:
            raise InvalidSubreddit('Invalid period `%s`' % period)
        if period and order not in ['top', 'controversial']:
            raise InvalidSubreddit('`%s` order does not allow sorting by'
                                   ' period' % order)

        # On some objects, praw doesn't allow you to pass arguments for the
        # order and period. Instead you need to call special helper functions
        # such as Multireddit.get_controversial_from_year(). Build the method
        # name here for convenience.
        if period:
            method_alias = 'get_{0}_from_{1}'.format(order, period)
        elif order:
            method_alias = 'get_{0}'.format(order)
        else:
            method_alias = 'get_hot'

        # Here's where we start to build the submission generators
        if query:
            if resource_root == 'u':
                search = '/r/{subreddit}/search'
                author = reddit.user.name if resource == 'me' else resource
                query = 'author:{0} {1}'.format(author, query)
                subreddit = None
            else:
                search = resource_root + '/{subreddit}/search'
                subreddit = None if resource == 'front' else resource

            reddit.config.API_PATHS['search'] = search
            submissions = reddit.search(query, subreddit=subreddit,
                                        sort=order, period=period)

        elif resource_root == 'domain':
            order = order or 'hot'
            submissions = reddit.get_domain_listing(
                resource, sort=order, period=period, limit=None)

        elif resource_root.endswith('/m'):
            redditor = resource_root.split('/')[1]
            multireddit = reddit.get_multireddit(redditor, resource)
            submissions = getattr(multireddit, method_alias)(limit=None)

        elif resource_root == 'u' and resource == 'me':
            if not reddit.is_oauth_session():
                raise exceptions.AccountError('Not logged in')
            else:
                order = order or 'new'
                submissions = reddit.user.get_submitted(sort=order, limit=None)

        elif resource_root == 'u' and resource == 'saved':
            if not reddit.is_oauth_session():
                raise exceptions.AccountError('Not logged in')
            else:
                order = order or 'new'
                submissions = reddit.user.get_saved(sort=order, limit=None)

        elif resource_root == 'u':
            order = order or 'new'
            period = period or 'all'
            redditor = reddit.get_redditor(resource)
            submissions = redditor.get_submitted(
                sort=order, time=period, limit=None)

        elif resource == 'front':
            if order in (None, 'hot'):
                submissions = reddit.get_front_page(limit=None)
            elif period:
                # For the front page, praw makes you send the period as `t`
                # instead of calling reddit.get_hot_from_week()
                method_alias = 'get_{0}'.format(order)
                method = getattr(reddit, method_alias)
                submissions = method(limit=None, params={'t': period})
            else:
                submissions = getattr(reddit, method_alias)(limit=None)

        else:
            subreddit = reddit.get_subreddit(resource)
            submissions = getattr(subreddit, method_alias)(limit=None)

            # For special subreddits like /r/random we want to replace the
            # display name with the one returned by the request.
            display_name = '/r/{0}'.format(subreddit.display_name)

        # We made it!
        return cls(display_name, submissions, loader, order=display_order)

    @property
    def range(self):
        # Note that for subreddits, the submissions are generated lazily and
        # there is no actual "end" index. Instead, we return the bottom index
        # that we have loaded so far.
        return 0, len(self._submission_data) - 1

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
                if hasattr(submission, 'title'):
                    data = self.strip_praw_submission(submission)
                else:
                    # when submission is a saved commment
                    data = self.strip_praw_comment(submission)

                data['index'] = len(self._submission_data) + 1
                # Add the post number to the beginning of the title
                data['title'] = '{0}. {1}'.format(data['index'], data['title'])
                self._submission_data.append(data)

        # Modifies the original dict, faster than copying
        data = self._submission_data[index]
        data['split_title'] = self.wrap_text(data['title'], width=n_cols)
        if len(data['split_title']) > self.max_title_rows:
            data['split_title'] = data['split_title'][:self.max_title_rows-1]
            data['split_title'].append('(Not enough space to display)')
        data['n_rows'] = len(data['split_title']) + 3
        data['offset'] = 0

        return data


class SubscriptionContent(Content):

    def __init__(self, name, subscriptions, loader):

        self.name = name
        self.order = None
        self._loader = loader
        self._subscriptions = subscriptions
        self._subscription_data = []

        try:
            self.get(0)
        except IndexError:
            raise exceptions.SubscriptionError('No content')

        # Load 1024 subscriptions up front (one http request's worth)
        # For most people this should be all of their subscriptions. Doing thi
        # allows the user to jump to the end of the page with `G`.
        if name != 'Popular Subreddits':
            try:
                self.get(1023)
            except IndexError:
                pass

    @classmethod
    def from_user(cls, reddit, loader, content_type='subreddit'):
        if content_type == 'subreddit':
            name = 'My Subreddits'
            items = reddit.get_my_subreddits(limit=None)
        elif content_type == 'multireddit':
            name = 'My Multireddits'
            # Multireddits are returned as a list
            items = iter(reddit.get_my_multireddits())
        elif content_type == 'popular':
            name = 'Popular Subreddits'
            items = reddit.get_popular_subreddits(limit=None)
        else:
            raise exceptions.SubscriptionError('Invalid type %s', content_type)

        return cls(name, items, loader)

    @property
    def range(self):
        return 0, len(self._subscription_data) - 1

    def get(self, index, n_cols=70):
        """
        Grab the `i`th object, with the title field formatted to fit
        inside of a window of width `n_cols`
        """

        if index < 0:
            raise IndexError

        while index >= len(self._subscription_data):
            try:
                with self._loader('Loading content'):
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

import textwrap
from datetime import datetime
from contextlib import contextmanager

import praw
import six

from .errors import SubmissionURLError, SubredditNameError

def clean(unicode_string):
    """
    Convert unicode string into ascii-safe characters.
    """

    if six.PY2:
        ascii_string = unicode_string.encode('ascii', 'replace')
    else:
        ascii_string = unicode_string.encode().decode('ascii', 'replace')

    ascii_string = ascii_string.replace('\\', '')
    return ascii_string


def strip_subreddit_url(permalink):
    """
    Grab the subreddit from the permalink because submission.subreddit.url
    makes a seperate call to the API.
    """

    subreddit = clean(permalink).split('/')[4]
    return '/r/{}'.format(subreddit)


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
        return ('%d minutes ago' % minutes) if verbose else ('%dmin' % minutes)
    hours = minutes // 60
    if hours < 24:
        return ('%d hours ago' % hours) if verbose else ('%dhr' % hours)
    days = hours // 24
    if days < 30:
        return ('%d days ago' % days) if verbose else ('%dday' % days)
    months = days // 30.4
    if months < 12:
        return ('%d months ago' % months) if verbose else ('%dmonth' % months)
    years = months // 12
    return ('%d years ago' % years) if verbose else ('%dyr' % years)

@contextmanager
def default_loader(self):
    yield

class BaseContent(object):

    def get(self, index, n_cols):
        raise NotImplementedError

    def iterate(self, index, step, n_cols):

        while True:

            # Hack to prevent displaying negative indicies if iterating in the
            # negative direction.
            if step < 0 and index < 0:
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
            nested = getattr(item, 'replies', None)
            if nested:
                for n in nested:
                    n.nested_level = item.nested_level + 1
                stack[0:0] = nested
            retval.append(item)
        return retval

    @staticmethod
    def strip_praw_comment(comment):
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
            data['body'] = 'More comments'.format(comment.count)
        else:
            data['type'] = 'Comment'
            data['body'] = clean(comment.body)
            data['created'] = humanize_timestamp(comment.created_utc)
            data['score'] = '{} pts'.format(comment.score)
            data['author'] = (clean(comment.author.name) if
                              getattr(comment, 'author') else '[deleted]')

            sub_author = (clean(comment.submission.author.name) if
                          getattr(comment.submission, 'author') else '[deleted]')
            data['is_author'] = (data['author'] == sub_author)

        return data

    @staticmethod
    def strip_praw_submission(sub):
        """
        Parse through a submission and return a dict with data ready to be
        displayed through the terminal.
        """

        is_selfpost = lambda s: s.startswith('http://www.reddit.com/r/')

        data = {}
        data['object'] = sub
        data['type'] = 'Submission'
        data['title'] = clean(sub.title)
        data['text'] = clean(sub.selftext)
        data['created'] = humanize_timestamp(sub.created_utc)
        data['comments'] = '{} comments'.format(sub.num_comments)
        data['score'] = '{} pts'.format(sub.score)
        data['author'] = (clean(sub.author.name) if getattr(sub, 'author')
                          else '[deleted]')
        data['permalink'] = clean(sub.permalink)
        data['subreddit'] = strip_subreddit_url(sub.permalink)
        data['url'] = ('(selfpost)' if is_selfpost(sub.url) else clean(sub.url))

        return data


class SubmissionContent(BaseContent):
    """
    Grab a submission from PRAW and lazily store comments to an internal
    list for repeat access.
    """

    def __init__(
            self,
            submission,
            loader=default_loader,
            indent_size=2,
            max_indent_level=4):

        self.indent_size = indent_size
        self.max_indent_level = max_indent_level
        self._loader = loader
        self._submission = submission
        self._submission_data = None
        self._comment_data = None
        self.name = None

        self.reset()

    @classmethod
    def from_url(
            cls,
            reddit,
            url,
            loader=default_loader,
            indent_size=2,
            max_indent_level=4):

        try:
            with loader():
                submission = reddit.get_submission(url)

        except praw.errors.APIException:
            raise SubmissionURLError(url)

        return cls(submission, loader, indent_size, max_indent_level)

    def reset(self):

        with self._loader():
            self._submission.refresh()
            self._submission_data = self.strip_praw_submission(self._submission)
            self.name = self._submission_data['permalink']
            comments = self.flatten_comments(self._submission.comments)
            self._comment_data = [self.strip_praw_comment(c) for c in comments]

    def get(self, index, n_cols=70):
        """
        Grab the `i`th submission, with the title field formatted to fit inside
        of a window of width `n`
        """

        if index < -1:
            raise IndexError

        elif index == -1:
            data = self._submission_data
            data['split_title'] = textwrap.wrap(data['title'], width=n_cols-2)
            data['split_text'] = textwrap.wrap(data['text'], width=n_cols-2)
            data['n_rows'] = (len(data['split_title']) + len(data['split_text']) + 5)
            data['offset'] = 0

        else:
            data = self._comment_data[index]
            indent_level = min(data['level'], self.max_indent_level)
            data['offset'] = indent_level * self.indent_size

            if data['type'] == 'Comment':
                data['split_body'] = textwrap.wrap(
                    data['body'], width=n_cols-data['offset'])
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
            for d in self.iterate(index+1, 1, n_cols):
                if d['level'] <= data['level']:
                    break

                count += d.get('count', 1)
                cache.append(d)

            comment = {}
            comment['type'] = 'HiddenComment'
            comment['cache'] = cache
            comment['count'] = count
            comment['level'] = data['level']
            comment['body'] = 'Hidden'.format(count)
            self._comment_data[index:index+len(cache)] = [comment]

        elif data['type'] == 'HiddenComment':
            self._comment_data[index:index+1] = data['cache']

        elif data['type'] == 'MoreComments':
            with self._loader():
                comments = data['object'].comments()
                comments = self.flatten_comments(comments, root_level=data['level'])
                comment_data = [self.strip_praw_comment(c) for c in comments]
                self._comment_data[index:index+1] = comment_data

        else:
            raise ValueError('% type not recognized' % data['type'])


class SubredditContent(BaseContent):
    """
    Grabs a subreddit from PRAW and lazily stores submissions to an internal
    list for repeat access.
    """

    def __init__(self, name, submissions, loader=default_loader):

        self.name = name
        self._loader = loader
        self._submissions = submissions
        self._submission_data = []

    @classmethod
    def from_name(cls, reddit, name, loader=default_loader):
        
        display_type = 'normal'

        if name == 'front':
            return cls('Front Page', reddit.get_front_page(limit=None), loader)

        if name == 'all':
            sub = reddit.get_subreddit(name)
        
        else:
            
            if '/' in name:
                name, display_type = name.split('/')

            try:
                with loader():
                    sub = reddit.get_subreddit(name, fetch=True)
            except praw.errors.ClientException:
                raise SubredditNameError(name)
        
        if display_type == 'top':
            return cls('/r/'+sub.display_name+'/top', sub.get_top_from_all(limit=None), loader)

        elif display_type == 'new':
            return cls('/r/'+sub.display_name+'/new', sub.get_new(limit=None), loader)

        else:
            return cls('/r/'+sub.display_name, sub.get_hot(limit=None), loader)

    def get(self, index, n_cols=70):
        """
        Grab the `i`th submission, with the title field formatted to fit inside
        of a window of width `n`
        """

        if index < 0:
            raise IndexError

        while index >= len(self._submission_data):

            try:
                with self._loader():
                    submission = next(self._submissions)
            except StopIteration:
                raise IndexError
            else:
                data = self.strip_praw_submission(submission)
                self._submission_data.append(data)

        # Modifies the original dict, faster than copying
        data = self._submission_data[index]
        data['split_title'] = textwrap.wrap(data['title'], width=n_cols)
        data['n_rows'] = len(data['split_title']) + 3
        data['offset'] = 0

        return data

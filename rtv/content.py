import textwrap
import praw

from utils import clean, strip_subreddit_url, humanize_timestamp

class ContainerBase(object):

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
            data['body'] = 'More comments [{}]'.format(comment.count)
        else:
            data['type'] = 'Comment'
            data['body'] = clean(comment.body)
            data['created'] = humanize_timestamp(comment.created_utc)
            data['score'] = '{} pts'.format(comment.score)
            data['author'] = (clean(comment.author.name) if
                              getattr(comment, 'author') else '[deleted]')

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

class SubredditContainer(ContainerBase):
    """
    Grabs a subreddit from PRAW and lazily stores submissions to an internal
    list for repeat access.
    """

    def __init__(self, reddit_session, subreddit='front'):
        """
        params:
            session (praw.Reddit): Active reddit connection
            subreddit (str): Subreddit to connect to, defaults to front page.
        """
        self.r = reddit_session
        self.r.config.decode_html_entities = True

        self.subreddit = None
        self.display_name = None
        self._submissions = None
        self._submission_data = None

        self.reset(subreddit=subreddit)

    def get(self, index, n_cols=70):
        """
        Grab the `i`th submission, with the title field formatted to fit inside
        of a window of width `n`
        """

        if index < 0:
            raise IndexError

        while index >= len(self._submission_data):

            try:
                submission = self._submissions.next()
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

    def iterate(self, index, step, n_cols):

        while True:
            yield self.get(index, n_cols)
            index += step

    def reset(self, subreddit=None):
        """
        Clear the internal list and fetch a new submission generator. Switch
        to the specified subreddit if one is given.
        """

        # Fall back to the internal value if nothing is passed in.
        self.subreddit = subreddit or self.subreddit
        self._submission_data = []

        if self.subreddit == 'front':
            self._submissions = self.r.get_front_page(limit=None)
            self.display_name = 'Front Page'
        else:
            sub = self.r.get_subreddit(self.subreddit)
            self._submissions = sub.get_hot()
            self.display_name = '/r/' + self.subreddit


class SubmissionContainer(ContainerBase):
    """
    Grabs a submission from PRAW and lazily store comments to an internal
    list for repeat access and to allow expanding and hiding comments.
    """

    def __init__(self, submission, indent_size=2, max_indent_level=4):

        self.submission = submission
        self.indent_size = indent_size
        self.max_indent_level = max_indent_level

        self.display_name = None
        self._submission_data = None
        self._comment_data = None

        self.reset()

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

    def toggle(self, index):
        """
        Toggle the state of the object at the given index.

        If it is a comment, pack it into a hidden comment.
        If it is a hidden comment, unpack it.
        If it is more comments, load the comments.
        """
        data = self.get(index)

        if data['type'] == 'Comment':
            cache = [data]
            count = 1
            for d in self.iterate(index+1, 1):
                if d['level'] <= data['level']:
                    break

                count += d.get('count', 1)
                cache.append(d)

            comment = {}
            comment['type'] = 'HiddenComment'
            comment['cache'] = cache
            comment['count'] = count
            comment['level'] = data['level']
            comment['body'] = 'Hidden [{}]'.format(count)
            self._comment_data[index:index+len(cache)] = [comment]

        elif data['type'] == 'HiddenComment':

            self._comment_data[index:index+1] = data['cache']

        elif data['type'] == 'MoreComments':

            comments = data['object'].comments()
            comments = self.flatten_comments(comments, root_level=data['level'])
            comment_data = [self.strip_praw_comment(c) for c in comments]
            self._comment_data[index:index+1] = comment_data

        else:
            raise ValueError('% type not recognized' % data['type'])

    def iterate(self, index, step, n_cols=70):

        while True:
            yield self.get(index, n_cols=n_cols)
            index += step

    def reset(self):
        """
        Fetch changes to the submission from PRAW and clear the internal list.
        """

        self.submission.refresh()
        self._submission_data = self.strip_praw_submission(self.submission)

        self.display_name = self._submission_data['permalink']
        comments = self.flatten_comments(self.submission.comments)
        self._comment_data = [self.strip_praw_comment(c) for c in comments]

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
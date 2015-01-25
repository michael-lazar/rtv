import textwrap

from utils import clean, strip_subreddit_url, humanize_timestamp

class SubmissionContent(object):
    """
    Facilitates navigating through the comments in a PRAW submission.
    """

    def __init__(self, submission):

        self.submission = submission
        self._comments = []


    @staticmethod
    def flatten_comments(submission):
        """
        Flatten a PRAW comment tree while preserving the nested level of each
        comment via the `nested_level` attribute.
        """

        stack = submission[:]
        for item in stack:
            item.nested_level = 0

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
        data['body'] = clean(comment.body)
        data['created'] = humanize_timestamp(comment.created_utc)
        data['score'] = '{} pts'.format(comment.score)
        data['author'] = (clean(comment.author.name) if
                          getattr(comment, 'author') else '[deleted]')

        return data


class SubredditContent(object):
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

    @staticmethod
    def strip_praw_submission(sub):
        """
        Parse through a submission and return a dict with data ready to be
        displayed through the terminal.
        """

        is_selfpost = lambda s: s.startswith('http://www.reddit.com/r/')

        data = {}
        data['title'] = clean(sub.title)
        data['text'] = clean(sub.selftext)
        data['created'] = humanize_timestamp(sub.created_utc)
        data['comments'] = '{} comments'.format(sub.num_comments)
        data['score'] = '{} pts'.format(sub.score)
        data['author'] = (clean(sub.author.name) if getattr(sub, 'author')
                          else '[deleted]')
        data['subreddit'] = strip_subreddit_url(sub.permalink)
        data['url'] = ('(selfpost)' if is_selfpost(sub.url) else clean(sub.url))

        return data

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
            self._submissions = self.r.get_subreddit(self.subreddit, limit=None)
            self.display_name = self._submissions.display_name
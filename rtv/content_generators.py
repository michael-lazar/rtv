from datetime import datetime, timedelta


def clean(unicode_string):
    """
    Convert unicode string into ascii-safe characters.
    """

    return unicode_string.encode('ascii', 'replace').replace('\\', '')


def humanize_timestamp(utc_timestamp, verbose=False):
    """
    Convert a utc timestamp into a human readable relative-time.
    """

    timedelta = datetime.utcnow() - datetime.utcfromtimestamp(utc_timestamp)

    seconds = int(timedelta.total_seconds())
    if seconds < 60:
        return 'moments ago' if verbose else '0min'
    minutes = seconds / 60
    if minutes < 60:
        return ('%d minutes ago' % minutes) if verbose else ('%dmin' % minutes)
    hours = minutes / 60
    if hours < 24:
        return ('%d hours ago' % hours) if verbose else ('%dhr' % hours)
    days = hours / 24
    if days < 30:
        return ('%d days ago' % days) if verbose else ('%dday' % days)
    months = days / 30.4
    if months < 12:
        return ('%d months ago' % months) if verbose else ('%dmonth' % months)
    years = months / 12
    return ('%d years ago' % years) if verbose else ('%dyr' % years)


class SubmissionGenerator(object):
    """
    Facilitates navigating through the comments in a PRAW submission.
    """

    def __init__(self, submission):

        self.submission = submission

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


class SubredditGenerator(object):
    """
    Grabs a subreddit from PRAW lazily and store in an internal list for repeat
    access.

    params:
        session (praw.Reddit): Active reddit connection
        subreddit (str): Subreddit to connect to, None defaults to front page.
    """

    def __init__(self, reddit_session, subreddit=None):

        self.r = reddit_session
        self.r.config.decode_html_entities = True

        if subreddit is None:
            self._submissions = self.r.get_front_page(limit=None)
        else:
            self._submissions = self.r.get_subreddit(subreddit, limit=None)

        self._submission_data = []

    @staticmethod
    def strip_praw_submission(sub):
        """
        Parse through a submission and return a dict with data ready to be
        displayed through the terminal.
        """

        is_selfpost = lambda s: s.startswith('http://www.reddit.com/r/')

        data = {}
        data['title'] = clean(sub.title)
        data['created'] = humanize_timestamp(sub.created_utc)
        data['comments'] = '{} comments'.format(sub.num_comments)
        data['score'] = '{} pts'.format(sub.score)
        data['author'] = clean(sub.author.name)
        data['subreddit'] = clean(sub.subreddit.url)
        data['url'] = ('(selfpost)' if is_selfpost(sub.url) else clean(sub.url))

        return data

    def get(self, index, n_cols):
        """
        Grab the `i`th submission, with the title field formatted to fit inside
        of a window of width `n`
        """

        assert(index >= 0)

        while index >= len(self._submission_data):
            data = self._strip_praw_submission(self._submissions.next())
            self._submission_data.append(data)

        # Modifies the original original dict, faster than copying
        data = self._submission_data[index]
        data['split_title'] = textwrap.wrap(data['title'], width=n_cols)
        data['n_rows'] = len(data['split_title']) + 3

        return data

    def iterate(self, index, n_cols):

        while True:
            yield self.get(index, n_cols)
            index += 1
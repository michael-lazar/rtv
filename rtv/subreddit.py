import praw
import textwrap
import curses

from utils import humanize_timestamp, flatten_tree, clean

def strip_submission(sub):
    "Grab info from a PRAW submission and prep for display."

    out = {}
    out['title'] = clean(sub.title)
    out['created'] = humanize_timestamp(sub.created_utc, long=False)
    out['comments'] = '{} comments'.format(sub.num_comments)
    out['score'] = '{} pts'.format(sub.score)
    out['author'] = clean(sub.author.name)
    out['subreddit'] = clean(sub.subreddit.url)
    out['url'] = ('(selfpost)' if sub.url.startswith('http://www.reddit.com/r/')
                  else clean(sub.url))

    return out

def draw_submission(win, data, top_down=True):
    "Draw a submission in the given window."

    win.erase()
    n_rows, n_cols = win.getmaxyx()
    n_cols -= 1  # Leave space for the cursor on the first line

    # Handle the case where the window is not large enough to fit the data.
    # Print as many rows as possible, either from the top down of the bottom up.
    valid_rows = range(0, n_rows)
    offset = 0 if top_down else -(data['n_rows'] - n_rows)

    n_title = len(data['split_title'])
    for row, text in enumerate(data['split_title'], start=offset):
        if row in valid_rows:
            win.addstr(row, 1, text)

    row = n_title
    if row in valid_rows:
        win.addnstr(row, 1, '{url}'.format(**data), n_cols)

    row = n_title + 1
    if row in valid_rows:
        win.addnstr(row, 1, '{created} {comments} {score}'.format(**data), n_cols)

    row = n_title + 2
    if row in valid_rows:
        win.addnstr(row, 1, '{author} {subreddit}'.format(**data), n_cols)


class SubmissionGenerator(object):
    """
    Grab submissions from PRAW lazily and store in an internal list for repeat
    access.
    """

    def __init__(self):

        self.r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
        self.r.config.decode_html_entities = True

        self._submissions = self.r.get_front_page(limit=None)
        self._submission_data = []

    def get(self, index, n_cols):

        assert(index >= 0)

        while index >= len(self._submission_data):
            data = strip_submission(self._submissions.next())
            self._submission_data.append(data)

        # Modifies the original original dict, faster than copying
        out = self._submission_data[index]
        out['split_title'] = textwrap.wrap(out['title'], width=n_cols)
        out['n_rows'] = len(out['split_title']) + 3

        return out

    def iterate(self, index, n_cols):

        while True:
            yield self.get(index, n_cols)
            index += 1



def draw_subreddit(stdscr):

    generator = SubmissionGenerator()

    main_window = stdscr.derwin(1, 0)
    main_window.erase()
    max_rows, max_cols = main_window.getmaxyx()

    submission_i, current_row = 0, 0
    for data in generator.iterate(submission_i, max_cols-1):
        n_rows = min(max_rows-current_row, data['n_rows'])
        sub_window = main_window.derwin(n_rows, max_cols, current_row, 0)
        draw_submission(sub_window, data)
        sub_window.refresh()  # Debugging
        current_row += n_rows + 1
        if current_row >= max_rows:
            break

    main_window.refresh()
    main_window.getch()

if __name__ == '__main__':

    #draw_submissions(None)
    curses.wrapper(draw_subreddit)
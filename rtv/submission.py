import textwrap
import curses

import praw

import utils

class OOBError(Exception):
    pass

class SubmissionDisplay(object):

    DEFAULT_REPLY_COLORS = [
        curses.COLOR_MAGENTA,
        curses.COLOR_GREEN,
        curses.COLOR_CYAN,
        curses.COLOR_YELLOW,
        ]

    def __init__(
            self,
            stdscr,
            max_indent_level=5,
            indent_size=1,
            reply_colors=None,
            ):

        self.stdscr = stdscr
        self.line = 0

        self._max_indent_level = max_indent_level
        self._indent_size = indent_size
        self._reply_colors = (reply_colors if reply_colors is not None
                              else self.DEFAULT_REPLY_COLORS)

    @staticmethod
    def clean(unicode_string):
        "Convert unicode string into ascii-safe characters."
        return unicode_string.encode('ascii', 'replace').replace('\\', '')

    def _get_reply_color(self, nested_level):
        return self._reply_colors[nested_level % len(self._reply_colors)]

    def _draw_post(self, submission):
        "Draw the sumbission author's post"

        n_rows, n_cols = self.stdscr.getmaxyx()
        n_cols -= 1

        title = textwrap.wrap(self.clean(submission.title), n_cols-1)
        indents = {'initial_indent':'  ', 'subsequent_indent':'  '}
        text = textwrap.wrap(self.clean(submission.selftext), n_cols-1, **indents)
        url = ([self.clean(submission.url)] if
                getattr(submission, 'url') else [])

        required_rows = 4 + len(text) + len(url) + len(title)
        if self.line + required_rows > n_rows:
            raise OOBError()

        win = self.stdscr.derwin(required_rows, n_cols, self.line, 0)
        submission.window = win
        win_y = 0
        self.line += required_rows

        win.hline(win_y, 0, curses.ACS_HLINE, n_cols)
        win_y += 1

        # Submission title
        color_attr = curses.color_pair(curses.COLOR_CYAN)
        win.addstr(win_y, 0, '\n'.join(title), color_attr|curses.A_BOLD)
        win_y += len(title)

        # Author / Date / Subreddit
        author = (self.clean(submission.author.name) if
                  getattr(submission, 'author') else '[deleted]')
        date = utils.humanize_timestamp(submission.created_utc)
        subreddit = self.clean(submission.subreddit.url)
        color_attr = curses.color_pair(curses.COLOR_GREEN)
        win.addstr(win_y, 0, author, curses.A_UNDERLINE|color_attr)
        win.addstr(' {} {}'.format(date, subreddit), curses.A_BOLD)
        win_y += 1

        if url:
            color_attr = curses.color_pair(curses.COLOR_MAGENTA)
            win.addstr(win_y, 0, url[0], curses.A_BOLD|color_attr)
            win_y += len(url)

        if text:
            win.addstr(win_y + len(url), 0, '\n'.join(text))
            win_y += len(text)

        # Score / Comments
        score = submission.score
        num_comments = submission.num_comments
        info = '{} points {} comments'.format(score, num_comments)
        win.addstr(win_y, 0, info, curses.A_BOLD)
        win_y += 1

        win.hline(win_y, 0, curses.ACS_HLINE, n_cols)


    def _draw_more_comments(self, comment):
        "Indicate that more comments can be loaded"

        n_rows, n_cols = self.stdscr.getmaxyx()
        n_cols -= 1

        required_rows = 2
        if self.line + required_rows > n_rows:
            raise OOBError()

        # Determine the indent level of the comment
        indent_level = min(self._max_indent_level, comment.nested_level)
        indent = indent_level * self._indent_size
        n_cols -= indent

        win = self.stdscr.derwin(required_rows, n_cols, self.line, indent)
        comment.window = win
        self.line += required_rows
        win.addnstr(0, indent, '[+] More comments', curses.A_BOLD)


    def _draw_comment(self, comment):
        "Draw a single comment"

        n_rows, n_cols = self.stdscr.getmaxyx()
        n_cols -= 1

        # Determine the indent level of the comment
        indent_level = min(self._max_indent_level, comment.nested_level)
        indent = indent_level * self._indent_size
        n_cols -= indent

        indents = {'initial_indent':' ', 'subsequent_indent':' '}
        text = textwrap.wrap(self.clean(comment.body), n_cols-1, **indents)

        required_rows = 2 + len(text)
        if self.line + required_rows > n_rows:
            raise OOBError()

        win = self.stdscr.derwin(required_rows, n_cols, self.line, indent)
        comment.window = win
        self.line += required_rows

        # Author / Score / Date
        author = (self.clean(comment.author.name) if
                  getattr(comment, 'author') else '[deleted]')
        date = utils.humanize_timestamp(comment.created_utc)
        score = submission.score
        color_attr = (curses.color_pair(curses.COLOR_GREEN) if comment.is_author
                      else curses.color_pair(curses.COLOR_BLUE))
        win.addstr(0, 1, author, curses.A_UNDERLINE|color_attr)
        win.addstr(' {} points {}'.format(score, date), curses.A_BOLD)

        # Body
        win.addstr(1, 0, '\n'.join(text))

        # Vertical line, unfortunately vline() doesn't support custom color so
        # we have to build it one chr at a time.
        reply_color = self._get_reply_color(comment.nested_level)
        color_attr = curses.color_pair(reply_color)
        for y in xrange(required_rows-1):
            win.addch(y, 0, curses.ACS_VLINE, color_attr)

    def _draw_url(self, submission):
        "Draw the submission url"

        n_rows, n_cols = self.stdscr.getmaxyx()

        color_attr = curses.color_pair(curses.COLOR_RED)
        url = self.clean(submission.permalink)
        self.stdscr.addnstr(self.line, 0, url, n_cols-1, color_attr|curses.A_STANDOUT)

        self.line += 1

        return True

    def draw_page(self, submission, comments, index=-1):
        """
        Draw the comments page starting at the given index.
        """

        # Initialize screen
        self.stdscr.erase()
        self.line = 0

        # URL is always drawn
        self._draw_url(submission)

        if index == -1:
            self._draw_post(submission)
            index += 1

        for comment in comments[index:]:
            try:
                if isinstance(comment, praw.objects.MoreComments):
                    self._draw_more_comments(comment)
                else:
                    comment.is_author = (comment.author == submission.author)
                    self._draw_comment(comment)

            except OOBError:
                break

        self.stdscr.refresh()

class SubmissionController(object):

    def __init__(self, display):

        self.display = display

        self._index = -1
        self._cursor = 0

    def loop(self, submission, comments):

        self.display.draw_page(submission, comments, self._index)

        while True:

            key = self.display.stdscr.getch()
            if key == curses.KEY_DOWN:
                self._index += 1
            elif key == curses.KEY_UP and self._index > -1:
                self._index -= 1
            elif key == curses.KEY_RESIZE:
                pass
            else:
                continue

            self.display.draw_page(submission, comments, self._index)


if __name__ == '__main__':

    r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
    r.config.decode_html_entities = True
    submissions = r.get_subreddit('all').get_hot(limit=5)
    submission = submissions.next()
    comments = utils.flatten_tree(submission.comments)


    with utils.curses_session() as stdscr:

        display = SubmissionDisplay(stdscr)
        controller = SubmissionController(display)
        controller.loop(submission, comments)
import praw
import textwrap
import curses

from content_generators import SubredditGenerator

class SubredditViewer(object):

    def __init__(self, stdscr):
        self.stdscr = stdscr

    def loop(self):

        while True:
            cmd = self.stdscr.getch()

            # Move cursor up one submission
            if cmd == curses.KEY_UP:
                self.move_cursor(-1)

            # Move cursor down one submission
            elif cmd == curses.KEY_DOWN:
                self.move_cursor(1)

            # View submission
            elif cmd in (curses.KEY_RIGHT, ord(' ')):
                pass

            # Enter edit mode to change subreddit
            elif cmd == ord('/'):
                pass

            # Refresh page
            elif cmd in (curses.KEY_F5, ord('r')):
                pass

            # Quit
            elif cmd == ord('q'):
                pass

            else:
                curses.beep()

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


def focus_submission(win):
    "Add a vertical column of reversed background on left side of the window"

    n_rows, n_cols = win.getmaxyx()
    for row in xrange(n_rows):
        win.chgat(row, 0, 1, curses.A_REVERSE)


def unfocus_submission(win):
    "Clear the vertical column"

    n_rows, n_cols = win.getmaxyx()
    for row in xrange(n_rows):
        win.chgat(row, 0, 1, curses.A_NORMAL)


def draw_subreddit(stdscr):

    r = praw.Reddit(user_agent='reddit terminal viewer (rtv) v0.0')
    generator = SubredditGenerator(r)

    main_window = stdscr.derwin(1, 0)
    main_window.erase()
    max_rows, max_cols = main_window.getmaxyx()

    submission_i, current_row = 0, 0
    for data in generator.iterate(submission_i, max_cols-1):
        n_rows = min(max_rows-current_row, data['n_rows'])
        sub_window = main_window.derwin(n_rows, max_cols, current_row, 0)
        draw_submission(sub_window, data)
        focus_submission(sub_window)
        sub_window.refresh()  # Debugging
        current_row += n_rows + 1
        if current_row >= max_rows:
            break

    main_window.refresh()
    main_window.getch()

if __name__ == '__main__':

    #draw_submissions(None)
    curses.wrapper(draw_subreddit)
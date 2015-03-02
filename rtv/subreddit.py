import curses
import sys
from requests.exceptions import HTTPError

from .errors import SubredditNameError
from .page import BasePage
from .submission import SubmissionPage
from .content import SubredditContent
from .utils import LoadScreen, text_input, display_message, Color, ESCAPE

class SubredditPage(BasePage):

    def __init__(self, stdscr, reddit, name):

        self.reddit = reddit
        self.name = name
        self.loader = LoadScreen(stdscr)

        content = SubredditContent.from_name(reddit, name, self.loader)
        super(SubredditPage, self).__init__(stdscr, content)

    def loop(self):

        self.draw()
        while True:
            cmd = self.stdscr.getch()

            if cmd in (curses.KEY_UP, ord('k')):
                self.move_cursor_up()
                self.clear_input_queue()

            elif cmd in (curses.KEY_DOWN, ord('j')):
                self.move_cursor_down()
                self.clear_input_queue()

            # View submission
            elif cmd in (curses.KEY_RIGHT, curses.KEY_ENTER, ord('l')):
                self.open_submission()
                self.draw()

            # Enter edit mode to change subreddit
            elif cmd == ord('/'):
                self.prompt_subreddit()
                self.draw()

            # Refresh page
            elif cmd in (curses.KEY_F5, ord('r')):
                self.refresh_content()
                self.draw()

            elif cmd == curses.KEY_RESIZE:
                self.draw()

            # Quit
            elif cmd == ord('q'):
                sys.exit()

            else:
                curses.beep()

    def refresh_content(self, name=None):

        name = name or self.name

        try:
            self.content = SubredditContent.from_name(
                self.reddit, name, self.loader)

        except (SubredditNameError, HTTPError):
            display_message(self.stdscr, 'Invalid Subreddit')

        else:
            self.nav.page_index, self.nav.cursor_index = 0, 0
            self.nav.inverted = False
            self.name = name

    def prompt_subreddit(self):

        attr = curses.A_BOLD | Color.MAGENTA
        prompt = 'Enter Subreddit: /r/'
        n_rows, n_cols = self.stdscr.getmaxyx()
        self.stdscr.addstr(n_rows-1, 0, prompt, attr)
        self.stdscr.refresh()
        window = self.stdscr.derwin(n_rows-1, len(prompt))
        window.attrset(attr)

        out = text_input(window)
        if out is not None:
            self.refresh_content(name=out)

    def open_submission(self):
        "Select the current submission to view posts"

        submission = self.content.get(self.nav.absolute_index)['object']
        page = SubmissionPage(self.stdscr, self.reddit, submission=submission)
        page.loop()

    @staticmethod
    def draw_item(win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                attr = curses.A_BOLD
                win.addstr(row, 1, text, attr)

        row = n_title + offset
        if row in valid_rows:
            attr = curses.A_UNDERLINE | Color.BLUE
            text = '{url}'.format(**data)
            win.addnstr(row, 1, text, n_cols-1, attr)

        row = n_title + offset + 1
        if row in valid_rows:
            text = '{created} {comments} {score}'.format(**data)
            win.addnstr(row, 1, text, n_cols-1)

        row = n_title + offset + 2
        if row in valid_rows:
            text = '{author}'.format(**data)
            win.addnstr(row, 1, text, n_cols-1, curses.A_BOLD)
            text = ' {subreddit}'.format(**data)
            win.addnstr(text, n_cols - win.getyx()[1], Color.YELLOW)

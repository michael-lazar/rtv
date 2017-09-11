"""
This file is a stub that contains the default RTV theme.

This will eventually be expanded to support loading/managing custom themes.
"""

import curses
from contextlib import contextmanager


DEFAULT_THEME = {
    'normal':                (-1,                   -1, curses.A_NORMAL),
    'bar_level_1':           (curses.COLOR_MAGENTA, -1, curses.A_NORMAL),
    'bar_level_1.selected':  (curses.COLOR_MAGENTA, -1, curses.A_REVERSE),
    'bar_level_2':           (curses.COLOR_CYAN,    -1, curses.A_NORMAL),
    'bar_level_2.selected':  (curses.COLOR_CYAN,    -1, curses.A_REVERSE),
    'bar_level_3':           (curses.COLOR_GREEN,   -1, curses.A_NORMAL),
    'bar_level_3.selected':  (curses.COLOR_GREEN,   -1, curses.A_REVERSE),
    'bar_level_4':           (curses.COLOR_YELLOW,  -1, curses.A_NORMAL),
    'bar_level_4.selected':  (curses.COLOR_YELLOW,  -1, curses.A_REVERSE),
    'comment_author':        (curses.COLOR_BLUE,    -1, curses.A_BOLD),
    'comment_author_self':   (curses.COLOR_GREEN,   -1, curses.A_BOLD),
    'comment_count':         (-1,                   -1, curses.A_NORMAL),
    'comment_text':          (-1,                   -1, curses.A_NORMAL),
    'created':               (-1,                   -1, curses.A_NORMAL),
    'cursor':                (-1,                   -1, curses.A_NORMAL),
    'cursor.selected':       (-1,                   -1, curses.A_REVERSE),
    'downvote':              (curses.COLOR_RED,     -1, curses.A_BOLD),
    'gold':                  (curses.COLOR_YELLOW,  -1, curses.A_BOLD),
    'help_bar':              (curses.COLOR_CYAN,    -1, curses.A_BOLD | curses.A_REVERSE),
    'hidden_comment_expand': (-1,                   -1, curses.A_BOLD),
    'hidden_comment_text':   (-1,                   -1, curses.A_NORMAL),
    'multireddit_name':      (curses.COLOR_YELLOW,  -1, curses.A_BOLD),
    'multireddit_text':      (-1,                   -1, curses.A_NORMAL),
    'neutral_vote':          (-1,                   -1, curses.A_BOLD),
    'notice_info':           (-1,                   -1, curses.A_NORMAL),
    'notice_loading':        (-1,                   -1, curses.A_NORMAL),
    'notice_error':          (-1,                   -1, curses.A_NORMAL),
    'notice_success':        (-1,                   -1, curses.A_NORMAL),
    'nsfw':                  (curses.COLOR_RED,     -1, curses.A_BOLD | curses.A_REVERSE),
    'order_bar':             (curses.COLOR_YELLOW,  -1, curses.A_BOLD),
    'order_bar.selected':    (curses.COLOR_YELLOW,  -1, curses.A_BOLD | curses.A_REVERSE),
    'prompt':                (curses.COLOR_CYAN,    -1, curses.A_BOLD | curses.A_REVERSE),
    'saved':                 (curses.COLOR_GREEN,   -1, curses.A_NORMAL),
    'score':                 (-1,                   -1, curses.A_NORMAL),
    'separator':             (-1,                   -1, curses.A_BOLD),
    'stickied':              (curses.COLOR_GREEN,   -1, curses.A_NORMAL),
    'subscription_name':     (curses.COLOR_YELLOW,  -1, curses.A_BOLD),
    'subscription_text':     (-1,                   -1, curses.A_NORMAL),
    'submission_author':     (curses.COLOR_GREEN,   -1, curses.A_NORMAL),
    'submission_flair':      (curses.COLOR_RED,     -1, curses.A_NORMAL),
    'submission_subreddit':  (curses.COLOR_YELLOW,  -1, curses.A_NORMAL),
    'submission_text':       (-1,                   -1, curses.A_NORMAL),
    'submission_title':      (-1,                   -1, curses.A_BOLD),
    'title_bar':             (curses.COLOR_CYAN,    -1, curses.A_BOLD | curses.A_REVERSE),
    'upvote':                (curses.COLOR_GREEN,   -1, curses.A_BOLD),
    'url':                   (curses.COLOR_BLUE,    -1, curses.A_UNDERLINE),
    'url_seen':              (curses.COLOR_MAGENTA, -1, curses.A_UNDERLINE),
    'user_flair':            (curses.COLOR_YELLOW,  -1, curses.A_BOLD)
}


class Theme(object):

    BAR_LEVELS = ['bar_level_1', 'bar_level_2', 'bar_level_3', 'bar_level_4']

    def __init__(self, monochrome=True):

        self.monochrome = monochrome
        self._modifier = None
        self._elements = {}
        self._color_pairs = {}

    def bind_curses(self):

        if self.monochrome:
            # Skip initializing the colors and just use the attributes
            self._elements = {key: val[2] for key, val in DEFAULT_THEME.items()}
            return

        # Shortcut for the default fg/bg
        self._color_pairs[(-1, -1)] = curses.A_NORMAL

        for key, (fg, bg, attr) in DEFAULT_THEME.items():
            # Register the color pair for the element
            if (fg, bg) not in self._color_pairs:
                index = len(self._color_pairs) + 1
                curses.init_pair(index, fg, bg)
                self._color_pairs[(fg, bg)] = curses.color_pair(index)

            self._elements[key] = self._color_pairs[(fg, bg)] | attr

    def get(self, element, modifier=None):

        modifier = modifier or self._modifier
        if modifier:
            modified_element = '{0}.{1}'.format(element, modifier)
            if modified_element in self._elements:
                return self._elements[modified_element]

        return self._elements[element]

    @contextmanager
    def set_modifier(self, modifier=None):

        # This case is undefined if the context manager is nested
        assert self._modifier is None

        self._modifier = modifier
        try:
            yield
        finally:
            self._modifier = None

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import os
import sys
import time
import curses
import locale
import threading
from types import MethodType
from collections import Counter

from vcr import VCR
from six.moves.urllib.parse import urlparse, parse_qs

from rtv.theme import Theme, ThemeList
from rtv.config import Config
from rtv.packages import praw
from rtv.oauth import OAuthHelper
from rtv.terminal import Terminal
from rtv.objects import curses_session
from rtv.subreddit_page import SubredditPage
from rtv.submission_page import SubmissionPage
from rtv.subscription_page import SubscriptionPage

try:
    from unittest import mock
except ImportError:
    import mock


def initialize_vcr():

    def auth_matcher(r1, r2):
        return (r1.headers.get('authorization') ==
                r2.headers.get('authorization'))

    def uri_with_query_matcher(r1, r2):
        p1,  p2 = urlparse(r1.uri), urlparse(r2.uri)
        return (p1[:3] == p2[:3] and
                parse_qs(p1.query, True) == parse_qs(p2.query, True))

    cassette_dir = os.path.join(os.path.dirname(__file__), 'cassettes')
    if not os.path.exists(cassette_dir):
        os.makedirs(cassette_dir)

    filename = os.path.join(cassette_dir, 'demo_theme.yaml')
    if os.path.exists(filename):
        record_mode = 'none'
    else:
        record_mode = 'once'
    vcr = VCR(
        record_mode=record_mode,
        filter_headers=[('Authorization', '**********')],
        filter_post_data_parameters=[('refresh_token', '**********')],
        match_on=['method', 'uri_with_query', 'auth', 'body'],
        cassette_library_dir=cassette_dir)
    vcr.register_matcher('auth', auth_matcher)
    vcr.register_matcher('uri_with_query', uri_with_query_matcher)

    return vcr


# Patch the getch method so we can display multiple notifications or
# other elements that require a keyboard input on the screen at the
# same time without blocking the main thread.
def notification_getch(self):
    if self.pause_getch:
        return -1
    return 0


def prompt_getch(self):
    while self.pause_getch:
        time.sleep(1)
    return 0


def draw_screen(stdscr, reddit, config, theme, oauth):

    threads = []
    max_y, max_x = stdscr.getmaxyx()
    mid_x = int(max_x / 2)
    tall_y, short_y = int(max_y / 3 * 2), int(max_y / 3)

    stdscr.clear()
    stdscr.refresh()

    # ===================================================================
    # Submission Page
    # ===================================================================
    win1 = stdscr.derwin(tall_y - 1, mid_x - 1, 0, 0)
    term = Terminal(win1, config)
    term.set_theme(theme)
    oauth.term = term

    url = 'https://www.reddit.com/r/Python/comments/4dy7xr'
    with term.loader('Loading'):
        page = SubmissionPage(reddit, term, config, oauth, url=url)

    # Tweak the data in order to demonstrate the full range of settings
    data = page.content.get(-1)
    data['object'].link_flair_text = 'flair'
    data['object'].gilded = 1
    data['object'].over_18 = True
    data['object'].saved = True
    data.update(page.content.strip_praw_submission(data['object']))
    data = page.content.get(0)
    data['object'].author.name = 'kafoozalum'
    data['object'].stickied = True
    data['object'].author_flair_text = 'flair'
    data['object'].likes = True
    data.update(page.content.strip_praw_comment(data['object']))
    data = page.content.get(1)
    data['object'].saved = True
    data['object'].likes = False
    data['object'].score_hidden = True
    data['object'].gilded = 1
    data.update(page.content.strip_praw_comment(data['object']))
    data = page.content.get(2)
    data['object'].author.name = 'kafoozalum'
    data['object'].body = data['object'].body[:100]
    data.update(page.content.strip_praw_comment(data['object']))
    page.content.toggle(9)
    page.content.toggle(5)
    page.draw()

    # ===================================================================
    # Subreddit Page
    # ===================================================================
    win2 = stdscr.derwin(tall_y - 1, mid_x - 1, 0, mid_x + 1)
    term = Terminal(win2, config)
    term.set_theme(theme)
    oauth.term = term

    with term.loader('Loading'):
        page = SubredditPage(reddit, term, config, oauth, '/u/saved')

    # Tweak the data in order to demonstrate the full range of settings
    data = page.content.get(3)
    data['object'].hide_score = True
    data['object'].author = None
    data['object'].saved = False
    data.update(page.content.strip_praw_submission(data['object']))
    page.content.order = 'rising'
    page.nav.cursor_index = 1
    page.draw()

    term.pause_getch = True
    term.getch = MethodType(notification_getch, term)
    thread = threading.Thread(target=term.show_notification,
                              args=('Success',),
                              kwargs={'style': 'Success'})
    thread.start()
    threads.append((thread, term))

    # ===================================================================
    # Subscription Page
    # ===================================================================
    win3 = stdscr.derwin(short_y, mid_x - 1, tall_y, 0)
    term = Terminal(win3, config)
    term.set_theme(theme)
    oauth.term = term

    with term.loader('Loading'):
        page = SubscriptionPage(reddit, term, config, oauth, 'popular')
    page.nav.cursor_index = 1
    page.draw()

    term.pause_getch = True
    term.getch = MethodType(notification_getch, term)
    thread = threading.Thread(target=term.show_notification,
                              args=('Error',),
                              kwargs={'style': 'Error'})
    thread.start()
    threads.append((thread, term))

    # ===================================================================
    # Multireddit Page
    # ===================================================================
    win4 = stdscr.derwin(short_y, mid_x - 1, tall_y, mid_x + 1)
    term = Terminal(win4, config)
    term.set_theme(theme)
    oauth.term = term

    with term.loader('Loading'):
        page = SubscriptionPage(reddit, term, config, oauth, 'multireddit')
    page.nav.cursor_index = 1
    page.draw()

    term.pause_getch = True
    term.getch = MethodType(notification_getch, term)
    thread = threading.Thread(target=term.show_notification,
                              args=('Info',),
                              kwargs={'style': 'Info'})
    thread.start()
    threads.append((thread, term))

    term = Terminal(win4, config)
    term.set_theme(theme)
    term.pause_getch = True
    term.getch = MethodType(prompt_getch, term)
    thread = threading.Thread(target=term.prompt_y_or_n, args=('Prompt: ',))
    thread.start()
    threads.append((thread, term))

    time.sleep(0.5)
    curses.curs_set(0)
    return threads


def main():

    locale.setlocale(locale.LC_ALL, '')

    if len(sys.argv) > 1:
        theme = Theme.from_name(sys.argv[1])
    else:
        theme = Theme()

    vcr = initialize_vcr()
    with vcr.use_cassette('demo_theme.yaml') as cassette, \
            curses_session() as stdscr:

        config = Config()
        if vcr.record_mode == 'once':
            config.load_refresh_token()
        else:
            config.refresh_token = 'mock_refresh_token'

        reddit = praw.Reddit(user_agent='RTV Theme Demo',
                             decode_html_entities=False,
                             disable_update_check=True)
        reddit.config.api_request_delay = 0

        config.history.add('https://api.reddit.com/comments/6llvsl/_/djutc3s')
        config.history.add('http://i.imgur.com/Z9iGKWv.gifv')
        config.history.add('https://www.reddit.com/r/Python/comments/6302cj/rpython_official_job_board/')

        term = Terminal(stdscr, config)
        term.set_theme()
        oauth = OAuthHelper(reddit, term, config)
        oauth.authorize()

        theme_list = ThemeList()

        while True:
            term = Terminal(stdscr, config)
            term.set_theme(theme)
            threads = draw_screen(stdscr, reddit, config, theme, oauth)

            try:
                ch = term.show_notification(theme.display_string)
            except KeyboardInterrupt:
                ch = Terminal.ESCAPE

            for thread, term in threads:
                term.pause_getch = False
                thread.join()

            if vcr.record_mode == 'once':
                break
            else:
                cassette.play_counts = Counter()

            theme_list.reload()

            if ch == curses.KEY_RIGHT:
                theme = theme_list.next(theme)
            elif ch == curses.KEY_LEFT:
                theme = theme_list.previous(theme)
            elif ch == Terminal.ESCAPE:
                break
            else:
                # Force the theme to reload
                theme = theme_list.next(theme)
                theme = theme_list.previous(theme)


sys.exit(main())


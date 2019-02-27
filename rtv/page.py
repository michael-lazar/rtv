# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import os
import sys
import time
import logging
from functools import wraps

import six
from kitchen.text.display import textual_width

from . import docs
from .clipboard import copy as clipboard_copy
from .objects import Controller, Command
from .exceptions import TemporaryFileError, ProgramError
from .__version__ import __version__

_logger = logging.getLogger(__name__)


def logged_in(f):
    """
    Decorator for Page methods that require the user to be authenticated.
    """

    @wraps(f)
    def wrapped_method(self, *args, **kwargs):
        if not self.reddit.is_oauth_session():
            self.term.show_notification('Not logged in')
            return None
        return f(self, *args, **kwargs)
    return wrapped_method


class PageController(Controller):
    character_map = {}


class Page(object):

    BANNER = None
    FOOTER = None

    def __init__(self, reddit, term, config, oauth):
        self.reddit = reddit
        self.term = term
        self.config = config
        self.oauth = oauth
        self.content = None
        self.nav = None
        self.controller = None

        self.active = True
        self.selected_page = None
        self._row = 0
        self._subwindows = None

    def refresh_content(self, order=None, name=None):
        raise NotImplementedError

    def _draw_item(self, win, data, inverted):
        raise NotImplementedError

    def get_selected_item(self):
        """
        Return the content dictionary that is currently selected by the cursor.
        """
        return self.content.get(self.nav.absolute_index)

    def loop(self):
        """
        Main control loop runs the following steps:
            1. Re-draw the screen
            2. Wait for user to press a key (includes terminal resizing)
            3. Trigger the method registered to the input key
            4. Check if there are any nested pages that need to be looped over

        The loop will run until self.active is set to False from within one of
        the methods.
        """
        self.active = True

        # This needs to be called once before the main loop, in case a subpage
        # was pre-selected before the loop started. This happens in __main__.py
        # with ``page.open_submission(url=url)``
        while self.selected_page and self.active:
            self.handle_selected_page()

        while self.active:
            self.draw()
            ch = self.term.stdscr.getch()
            self.controller.trigger(ch)

            while self.selected_page and self.active:
                self.handle_selected_page()

        return self.selected_page

    def handle_selected_page(self):
        """
        Some commands will result in an action that causes a new page to open.
        Examples include selecting a submission, viewing subscribed subreddits,
        or opening the user's inbox. With these commands, the newly selected
        page will be pre-loaded and stored in ``self.selected_page`` variable.
        It's up to each page type to determine what to do when another page is
        selected.

          - It can start a nested page.loop(). This would allow the user to
            return to their previous screen after exiting the sub-page. For
            example, this is what happens when opening an individual submission
            from within a subreddit page. When the submission is closed, the
            user resumes the subreddit that they were previously viewing.

          - It can close the current self.loop() and bubble the selected page up
            one level in the loop stack. For example, this is what happens when
            the user opens their subscriptions and selects a subreddit. The
            subscription page loop is closed and the selected subreddit is
            bubbled up to the root level loop.

        Care should be taken to ensure the user can never enter an infinite
        nested loop, as this could lead to memory leaks and recursion errors.

            # Example of an unsafe nested loop
            subreddit_page.loop()
                -> submission_page.loop()
                    -> subreddit_page.loop()
                        -> submission_page.loop()
                            ...

        """
        raise NotImplementedError

    @PageController.register(Command('REFRESH'))
    def reload_page(self):
        """
        Clear the PRAW cache to force the page the re-fetch content from reddit.
        """
        self.reddit.handler.clear_cache()
        self.refresh_content()

    @PageController.register(Command('EXIT'))
    def exit(self):
        """
        Prompt and exit the application.
        """
        if self.term.prompt_y_or_n('Do you really want to quit? (y/n): '):
            sys.exit()

    @PageController.register(Command('FORCE_EXIT'))
    def force_exit(self):
        """
        Immediately exit the application.
        """
        sys.exit()

    @PageController.register(Command('PREVIOUS_THEME'))
    def previous_theme(self):
        """
        Cycle to preview the previous theme from the internal list of themes.
        """
        theme = self.term.theme_list.previous(self.term.theme)
        while not self.term.check_theme(theme):
            theme = self.term.theme_list.previous(theme)

        self.term.set_theme(theme)
        self.draw()
        message = self.term.theme.display_string
        self.term.show_notification(message, timeout=1)

    @PageController.register(Command('NEXT_THEME'))
    def next_theme(self):
        """
        Cycle to preview the next theme from the internal list of themes.
        """
        theme = self.term.theme_list.next(self.term.theme)
        while not self.term.check_theme(theme):
            theme = self.term.theme_list.next(theme)

        self.term.set_theme(theme)
        self.draw()
        message = self.term.theme.display_string
        self.term.show_notification(message, timeout=1)

    @PageController.register(Command('HELP'))
    def show_help(self):
        """
        Open the help documentation in the system pager.
        """
        self.term.open_pager(docs.HELP.strip())

    @PageController.register(Command('MOVE_UP'))
    def move_cursor_up(self):
        """
        Move the cursor up one selection.
        """
        self._move_cursor(-1)
        self.clear_input_queue()

    @PageController.register(Command('MOVE_DOWN'))
    def move_cursor_down(self):
        """
        Move the cursor down one selection.
        """
        self._move_cursor(1)
        self.clear_input_queue()

    @PageController.register(Command('PAGE_UP'))
    def move_page_up(self):
        """
        Move the cursor up approximately the number of entries on the page.
        """
        self._move_page(-1)
        self.clear_input_queue()

    @PageController.register(Command('PAGE_DOWN'))
    def move_page_down(self):
        """
        Move the cursor down approximately the number of entries on the page.
        """
        self._move_page(1)
        self.clear_input_queue()

    @PageController.register(Command('PAGE_TOP'))
    def move_page_top(self):
        """
        Move the cursor to the first item on the page.
        """
        self.nav.page_index = self.content.range[0]
        self.nav.cursor_index = 0
        self.nav.inverted = False

    @PageController.register(Command('PAGE_BOTTOM'))
    def move_page_bottom(self):
        """
        Move the cursor to the last item on the page.
        """
        self.nav.page_index = self.content.range[1]
        self.nav.cursor_index = 0
        self.nav.inverted = True

    @PageController.register(Command('UPVOTE'))
    @logged_in
    def upvote(self):
        """
        Upvote the currently selected item.
        """
        data = self.get_selected_item()
        if 'likes' not in data:
            self.term.flash()
        elif getattr(data['object'], 'archived'):
            self.term.show_notification("Voting disabled for archived post", style='Error')
        elif data['likes']:
            with self.term.loader('Clearing vote'):
                data['object'].clear_vote()
            if not self.term.loader.exception:
                data['likes'] = None
        else:
            with self.term.loader('Voting'):
                data['object'].upvote()
            if not self.term.loader.exception:
                data['likes'] = True

    @PageController.register(Command('DOWNVOTE'))
    @logged_in
    def downvote(self):
        """
        Downvote the currently selected item.
        """
        data = self.get_selected_item()
        if 'likes' not in data:
            self.term.flash()
        elif getattr(data['object'], 'archived'):
            self.term.show_notification("Voting disabled for archived post", style='Error')
        elif data['likes'] or data['likes'] is None:
            with self.term.loader('Voting'):
                data['object'].downvote()
            if not self.term.loader.exception:
                data['likes'] = False
        else:
            with self.term.loader('Clearing vote'):
                data['object'].clear_vote()
            if not self.term.loader.exception:
                data['likes'] = None

    @PageController.register(Command('SAVE'))
    @logged_in
    def save(self):
        """
        Mark the currently selected item as saved through the reddit API.
        """
        data = self.get_selected_item()
        if 'saved' not in data:
            self.term.flash()
        elif not data['saved']:
            with self.term.loader('Saving'):
                data['object'].save()
            if not self.term.loader.exception:
                data['saved'] = True
        else:
            with self.term.loader('Unsaving'):
                data['object'].unsave()
            if not self.term.loader.exception:
                data['saved'] = False

    @PageController.register(Command('LOGIN'))
    def login(self):
        """
        Prompt to log into the user's account, or log out of the current
        account.
        """
        if self.reddit.is_oauth_session():
            ch = self.term.show_notification('Log out? (y/n)')
            if ch in (ord('y'), ord('Y')):
                self.oauth.clear_oauth_data()
                self.term.show_notification('Logged out')
        else:
            self.oauth.authorize()

    def reply(self):
        """
        Reply to the selected item. This is a utility method and should not
        be bound to a key directly.

        Item type:
            Submission - add a top level comment
            Comment - add a comment reply
            Message - reply to a private message
        """
        data = self.get_selected_item()

        if data['type'] == 'Submission':
            body = data['text']
            description = 'submission'
            reply = data['object'].add_comment
        elif data['type'] in ('Comment', 'InboxComment'):
            body = data['body']
            description = 'comment'
            reply = data['object'].reply
        elif data['type'] == 'Message':
            body = data['body']
            description = 'private message'
            reply = data['object'].reply
        else:
            self.term.flash()
            return

        # Construct the text that will be displayed in the editor file.
        # The post body will be commented out and added for reference
        lines = ['  |' + line for line in body.split('\n')]
        content = '\n'.join(lines)
        comment_info = docs.REPLY_FILE.format(
            author=data['author'],
            type=description,
            content=content)

        with self.term.open_editor(comment_info) as comment:
            if not comment:
                self.term.show_notification('Canceled')
                return

            with self.term.loader('Posting {}'.format(description), delay=0):
                reply(comment)
                # Give reddit time to process the submission
                time.sleep(2.0)

            if self.term.loader.exception is None:
                self.reload_page()
            else:
                raise TemporaryFileError()

    @PageController.register(Command('DELETE'))
    @logged_in
    def delete_item(self):
        """
        Delete a submission or comment.
        """
        data = self.get_selected_item()
        if data.get('author') != self.reddit.user.name:
            self.term.flash()
            return

        prompt = 'Are you sure you want to delete this? (y/n): '
        if not self.term.prompt_y_or_n(prompt):
            self.term.show_notification('Canceled')
            return

        with self.term.loader('Deleting', delay=0):
            data['object'].delete()
            # Give reddit time to process the request
            time.sleep(2.0)

        if self.term.loader.exception is None:
            self.reload_page()

    @PageController.register(Command('EDIT'))
    @logged_in
    def edit(self):
        """
        Edit a submission or comment.
        """
        data = self.get_selected_item()
        if data.get('author') != self.reddit.user.name:
            self.term.flash()
            return

        if data['type'] == 'Submission':
            content = data['text']
            info = docs.SUBMISSION_EDIT_FILE.format(
                content=content, id=data['object'].id)
        elif data['type'] == 'Comment':
            content = data['body']
            info = docs.COMMENT_EDIT_FILE.format(
                content=content, id=data['object'].id)
        else:
            self.term.flash()
            return

        with self.term.open_editor(info) as text:
            if not text or text == content:
                self.term.show_notification('Canceled')
                return

            with self.term.loader('Editing', delay=0):
                data['object'].edit(text)
                time.sleep(2.0)

            if self.term.loader.exception is None:
                self.reload_page()
            else:
                raise TemporaryFileError()

    @PageController.register(Command('PRIVATE_MESSAGE'))
    @logged_in
    def send_private_message(self):
        """
        Send a new private message to another user.
        """
        message_info = docs.MESSAGE_FILE
        with self.term.open_editor(message_info) as text:
            if not text:
                self.term.show_notification('Canceled')
                return

            parts = text.split('\n', 2)
            if len(parts) == 1:
                self.term.show_notification('Missing message subject')
                return
            elif len(parts) == 2:
                self.term.show_notification('Missing message body')
                return

            recipient, subject, message = parts
            recipient = recipient.strip()
            subject = subject.strip()
            message = message.rstrip()

            if not recipient:
                self.term.show_notification('Missing recipient')
                return
            elif not subject:
                self.term.show_notification('Missing message subject')
                return
            elif not message:
                self.term.show_notification('Missing message body')
                return

            with self.term.loader('Sending message', delay=0):
                self.reddit.send_message(
                    recipient, subject, message, raise_captcha_exception=True)
                # Give reddit time to process the message
                time.sleep(2.0)

            if self.term.loader.exception:
                raise TemporaryFileError()
            else:
                self.term.show_notification('Message sent!')
                self.selected_page = self.open_inbox_page('sent')

    def prompt_and_select_link(self):
        """
        Prompt the user to select a link from a list to open.

        Return the link that was selected, or ``None`` if no link was selected.
        """
        data = self.get_selected_item()
        url_full = data.get('url_full')
        permalink = data.get('permalink')

        if url_full and url_full != permalink:
            # The item is a link-only submission that won't contain text
            link = url_full
        else:
            html = data.get('html')
            if html:
                extracted_links = self.content.extract_links(html)
                if not extracted_links:
                    # Only one selection to choose from, so just pick it
                    link = permalink
                else:
                    # Let the user decide which link to open
                    links = []
                    if permalink:
                        links += [{'text': 'Permalink', 'href': permalink}]
                    links += extracted_links
                    link = self.term.prompt_user_to_select_link(links)
            else:
                # Some items like hidden comments don't have any HTML to parse
                link = permalink

        return link

    @PageController.register(Command('COPY_PERMALINK'))
    def copy_permalink(self):
        """
        Copy the submission permalink to OS clipboard
        """
        url = self.get_selected_item().get('permalink')
        self.copy_to_clipboard(url)

    @PageController.register(Command('COPY_URL'))
    def copy_url(self):
        """
        Copy a link to OS clipboard
        """
        url = self.prompt_and_select_link()
        self.copy_to_clipboard(url)

    def copy_to_clipboard(self, url):
        """
        Attempt to copy the selected URL to the user's clipboard
        """
        if url is None:
            self.term.flash()
            return

        try:
            clipboard_copy(url)
        except (ProgramError, OSError) as e:
            _logger.exception(e)
            self.term.show_notification(
                'Failed to copy url: {0}'.format(e))
        else:
            self.term.show_notification(
                ['Copied to clipboard:', url], timeout=1)

    @PageController.register(Command('SUBSCRIPTIONS'))
    @logged_in
    def subscriptions(self):
        """
        View a list of the user's subscribed subreddits
        """
        self.selected_page = self.open_subscription_page('subreddit')

    @PageController.register(Command('MULTIREDDITS'))
    @logged_in
    def multireddits(self):
        """
        View a list of the user's subscribed multireddits
        """
        self.selected_page = self.open_subscription_page('multireddit')

    @PageController.register(Command('PROMPT'))
    def prompt(self):
        """
        Open a prompt to navigate to a different subreddit or comment"
        """
        name = self.term.prompt_input('Enter page: /')
        if name:
            # Check if opening a submission url or a subreddit url
            # Example patterns for submissions:
            #     comments/571dw3
            #     /comments/571dw3
            #     /r/pics/comments/571dw3/
            #     https://www.reddit.com/r/pics/comments/571dw3/at_disneyland
            submission_pattern = re.compile(r'(^|/)comments/(?P<id>.+?)($|/)')

            match = submission_pattern.search(name)
            if match:
                url = 'https://www.reddit.com/comments/{0}'.format(match.group('id'))
                self.selected_page = self.open_submission_page(url)
            else:
                self.selected_page = self.open_subreddit_page(name)

    @PageController.register(Command('INBOX'))
    @logged_in
    def inbox(self):
        """
        View the user's inbox.
        """
        self.selected_page = self.open_inbox_page('all')

    def open_inbox_page(self, content_type):
        """
        Open an instance of the inbox page for the logged in user.
        """
        from .inbox_page import InboxPage

        with self.term.loader('Loading inbox'):
            page = InboxPage(self.reddit, self.term, self.config, self.oauth,
                             content_type=content_type)
        if not self.term.loader.exception:
            return page

    def open_subscription_page(self, content_type):
        """
        Open an instance of the subscriptions page with the selected content.
        """
        from .subscription_page import SubscriptionPage

        with self.term.loader('Loading {0}s'.format(content_type)):
            page = SubscriptionPage(self.reddit, self.term, self.config,
                                    self.oauth, content_type=content_type)
        if not self.term.loader.exception:
            return page

    def open_submission_page(self, url=None, submission=None):
        """
        Open an instance of the submission page for the given submission URL.
        """
        from .submission_page import SubmissionPage

        with self.term.loader('Loading submission'):
            page = SubmissionPage(self.reddit, self.term, self.config,
                                  self.oauth, url=url, submission=submission)
        if not self.term.loader.exception:
            return page

    def open_subreddit_page(self, name):
        """
        Open an instance of the subreddit page for the given subreddit name.
        """
        from .subreddit_page import SubredditPage

        with self.term.loader('Loading subreddit'):
            page = SubredditPage(self.reddit, self.term, self.config,
                                 self.oauth, name)
        if not self.term.loader.exception:
            return page

    def clear_input_queue(self):
        """
        Clear excessive input caused by the scroll wheel or holding down a key
        """
        with self.term.no_delay():
            while self.term.getch() != -1:
                continue

    def draw(self):
        """
        Clear the terminal screen and redraw all of the sub-windows
        """
        n_rows, n_cols = self.term.stdscr.getmaxyx()
        if n_rows < self.term.MIN_HEIGHT or n_cols < self.term.MIN_WIDTH:
            # TODO: Will crash when you try to navigate if the terminal is too
            # small at startup because self._subwindows will never be populated
            return

        self._row = 0
        self._draw_header()
        self._draw_banner()
        self._draw_content()
        self._draw_footer()
        self.term.clear_screen()
        self.term.stdscr.refresh()

    def _draw_header(self):
        """
        Draw the title bar at the top of the screen
        """
        n_rows, n_cols = self.term.stdscr.getmaxyx()

        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        # curses.bkgd expects bytes in py2 and unicode in py3
        window.bkgd(str(' '), self.term.attr('TitleBar'))

        sub_name = self.content.name
        sub_name = sub_name.replace('/r/front', 'Front Page')

        parts = sub_name.split('/')
        if len(parts) == 1:
            pass
        elif '/m/' in sub_name:
            _, _, user, _, multi = parts
            sub_name = '{} Curated by {}'.format(multi, user)
        elif parts[1] == 'u':
            noun = 'My' if parts[2] == 'me' else parts[2] + "'s"
            user_room = parts[3] if len(parts) == 4 else 'overview'
            title_lookup = {
                'overview': 'Overview',
                'submitted': 'Submissions',
                'comments': 'Comments',
                'saved': 'Saved Content',
                'hidden': 'Hidden Content',
                'upvoted': 'Upvoted Content',
                'downvoted': 'Downvoted Content'
            }
            sub_name = "{} {}".format(noun, title_lookup[user_room])

        query = self.content.query
        if query:
            sub_name = 'Searching {0}: {1}'.format(sub_name, query)
        self.term.add_line(window, sub_name, 0, 0)

        # Set the terminal title
        if len(sub_name) > 50:
            title = sub_name.strip('/')
            title = title.replace('_', ' ')
            try:
                title = title.rsplit('/', 1)[1]
            except IndexError:
                pass
        else:
            title = sub_name

        # Setting the terminal title will break emacs or systems without
        # X window.
        if os.getenv('DISPLAY') and not os.getenv('INSIDE_EMACS'):
            title += ' - rtv {0}'.format(__version__)
            title = self.term.clean(title)
            if six.PY3:
                # In py3 you can't write bytes to stdout
                title = title.decode('utf-8')
                title = '\x1b]2;{0}\x07'.format(title)
            else:
                title = b'\x1b]2;{0}\x07'.format(title)
            sys.stdout.write(title)
            sys.stdout.flush()

        if self.reddit and self.reddit.user is not None:
            # The starting position of the name depends on if we're converting
            # to ascii or not
            width = len if self.config['ascii'] else textual_width

            if self.config['hide_username']:
                username = "Logged in"
            else:
                username = self.reddit.user.name
            s_col = (n_cols - width(username) - 1)
            # Only print username if it fits in the empty space on the right
            if (s_col - 1) >= width(sub_name):
                self.term.add_line(window, username, 0, s_col)

        self._row += 1

    def _draw_banner(self):
        """
        Draw the banner with sorting options at the top of the page
        """
        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        window.bkgd(str(' '), self.term.attr('OrderBar'))

        banner = docs.BANNER_SEARCH if self.content.query else self.BANNER
        items = banner.strip().split(' ')

        distance = (n_cols - sum(len(t) for t in items) - 1) / (len(items) - 1)
        spacing = max(1, int(distance)) * ' '
        text = spacing.join(items)
        self.term.add_line(window, text, 0, 0)
        if self.content.order is not None:
            order = self.content.order.split('-')[0]
            col = text.find(order) - 3
            attr = self.term.attr('OrderBarHighlight')
            window.chgat(0, col, 3, attr)

        self._row += 1

    def _draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """
        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(n_rows - self._row - 1, n_cols, self._row, 0)
        window.erase()
        win_n_rows, win_n_cols = window.getmaxyx()

        self._subwindows = []
        page_index, cursor_index, inverted = self.nav.position
        step = self.nav.step

        # If not inverted, align the first submission with the top and draw
        # downwards. If inverted, align the first submission with the bottom
        # and draw upwards.
        cancel_inverted = True
        current_row = (win_n_rows - 1) if inverted else 0
        available_rows = win_n_rows
        top_item_height = None if inverted else self.nav.top_item_height
        for data in self.content.iterate(page_index, step, win_n_cols - 2):
            subwin_n_rows = min(available_rows, data['n_rows'])
            subwin_inverted = inverted
            if top_item_height is not None:
                # Special case: draw the page as non-inverted, except for the
                # top element. This element will be drawn as inverted with a
                # restricted height
                subwin_n_rows = min(subwin_n_rows, top_item_height)
                subwin_inverted = True
                top_item_height = None
            subwin_n_cols = win_n_cols - data['h_offset']
            start = current_row - subwin_n_rows + 1 if inverted else current_row
            subwindow = window.derwin(subwin_n_rows, subwin_n_cols, start, data['h_offset'])
            self._subwindows.append((subwindow, data, subwin_inverted))
            available_rows -= (subwin_n_rows + 1)  # Add one for the blank line
            current_row += step * (subwin_n_rows + 1)
            if available_rows <= 0:
                # Indicate the page is full and we can keep the inverted screen.
                cancel_inverted = False
                break

        if len(self._subwindows) == 1:
            # Never draw inverted if only one subwindow. The top of the
            # subwindow should always be aligned with the top of the screen.
            cancel_inverted = True

        if cancel_inverted and self.nav.inverted:
            # In some cases we need to make sure that the screen is NOT
            # inverted. Unfortunately, this currently means drawing the whole
            # page over again. Could not think of a better way to pre-determine
            # if the content will fill up the page, given that it is dependent
            # on the size of the terminal.
            self.nav.flip((len(self._subwindows) - 1))
            self._draw_content()
            return

        if self.nav.cursor_index >= len(self._subwindows):
            # Don't allow the cursor to go over the number of subwindows
            # This could happen if the window is resized and the cursor index is
            # pushed out of bounds
            self.nav.cursor_index = len(self._subwindows) - 1

        # Now that the windows are setup, we can take a second pass through
        # to draw the text onto each subwindow
        for index, (win, data, inverted) in enumerate(self._subwindows):
            if self.nav.absolute_index >= 0 and index == self.nav.cursor_index:
                win.bkgd(str(' '), self.term.attr('Selected'))
                with self.term.theme.turn_on_selected():
                    self._draw_item(win, data, inverted)
            else:
                win.bkgd(str(' '), self.term.attr('Normal'))
                self._draw_item(win, data, inverted)

        self._row += win_n_rows

    def _draw_footer(self):
        """
        Draw the key binds help bar at the bottom of the screen
        """
        n_rows, n_cols = self.term.stdscr.getmaxyx()
        window = self.term.stdscr.derwin(1, n_cols, self._row, 0)
        window.erase()
        window.bkgd(str(' '), self.term.attr('HelpBar'))

        text = self.FOOTER.strip()
        self.term.add_line(window, text, 0, 0)
        self._row += 1

    def _move_cursor(self, direction):
        # Note: ACS_VLINE doesn't like changing the attribute, so disregard the
        # redraw flag and opt to always redraw
        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            self.term.flash()

    def _move_page(self, direction):
        valid, redraw = self.nav.move_page(direction, len(self._subwindows)-1)
        if not valid:
            self.term.flash()

    def _prompt_period(self, order):
        choices = {
            '\n': order,
            '1': '{0}-hour'.format(order),
            '2': '{0}-day'.format(order),
            '3': '{0}-week'.format(order),
            '4': '{0}-month'.format(order),
            '5': '{0}-year'.format(order),
            '6': '{0}-all'.format(order)}

        message = docs.TIME_ORDER_MENU.strip().splitlines()
        ch = self.term.show_notification(message)
        ch = six.unichr(ch)
        return choices.get(ch)

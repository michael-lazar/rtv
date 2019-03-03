# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import os
import curses
import codecs
from textwrap import dedent

import six
import pytest

from rtv.theme import Theme
from rtv.docs import (HELP, REPLY_FILE, COMMENT_EDIT_FILE, TOKEN,
                      SUBMISSION_FILE, SUBMISSION_EDIT_FILE, MESSAGE_FILE)
from rtv.exceptions import TemporaryFileError, BrowserError

try:
    from unittest import mock
except ImportError:
    import mock


def test_terminal_properties(terminal, config):

    assert isinstance(terminal.up_arrow, six.text_type)
    assert isinstance(terminal.down_arrow, six.text_type)
    assert isinstance(terminal.neutral_arrow, six.text_type)
    assert isinstance(terminal.gilded, six.text_type)

    terminal._display = None
    with mock.patch('rtv.terminal.sys') as sys, \
            mock.patch.dict('os.environ', {'DISPLAY': ''}):
        sys.platform = 'linux'
        assert terminal.display is False

    terminal._display = None
    with mock.patch('rtv.terminal.sys') as sys, \
            mock.patch('os.environ', {'DISPLAY': ''}), \
            mock.patch('webbrowser._tryorder', new=[]):
        sys.platform = 'darwin'
        assert terminal.display is True

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': ':0', 'BROWSER': 'w3m'}):
        assert terminal.display is False

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': ':0', 'BROWSER': ''}), \
            mock.patch('webbrowser._tryorder'):
        assert terminal.display is True

    assert terminal.get_arrow(None) is not None
    assert terminal.get_arrow(True) is not None
    assert terminal.get_arrow(False) is not None
    assert terminal.config == config
    assert terminal.loader is not None

    assert terminal.MIN_HEIGHT is not None
    assert terminal.MIN_WIDTH is not None

    assert terminal.theme is not None


def test_terminal_functions(terminal):

    terminal.flash()
    assert curses.flash.called

    terminal.getch()
    assert terminal.stdscr.getch.called

    with pytest.raises(RuntimeError):
        with terminal.no_delay():
            raise RuntimeError()
    terminal.stdscr.nodelay.assert_any_call(0)
    terminal.stdscr.nodelay.assert_any_call(1)

    curses.endwin.reset_mock()
    curses.doupdate.reset_mock()
    with terminal.suspend():
        pass
    assert curses.endwin.called
    assert curses.doupdate.called

    curses.endwin.reset_mock()
    curses.doupdate.reset_mock()
    with pytest.raises(RuntimeError):
        with terminal.suspend():
            raise RuntimeError()
    assert curses.endwin.called
    assert curses.doupdate.called

    terminal.addch(terminal.stdscr, 3, 5, 'ch', 'attr')
    terminal.stdscr.addch.assert_called_with(3, 5, 'ch', 'attr')


def test_terminal_no_flash(terminal):

    terminal.config['flash'] = False
    terminal.flash()
    assert not curses.flash.called


def test_terminal_clean_ascii(terminal):

    terminal.config['ascii'] = True

    # unicode returns ascii
    text = terminal.clean('hello ❤')
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii') == 'hello ?'

    # utf-8 returns ascii
    text = terminal.clean('hello ❤'.encode('utf-8'))
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii') == 'hello ?'

    # ascii returns ascii
    text = terminal.clean('hello'.encode('ascii'))
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii') == 'hello'


def test_terminal_clean_unicode(terminal):

    terminal.config['ascii'] = False

    # unicode returns utf-8
    text = terminal.clean('hello ❤')
    assert isinstance(text, six.binary_type)
    assert text.decode('utf-8') == 'hello ❤'

    # utf-8 returns utf-8
    text = terminal.clean('hello ❤'.encode('utf-8'))
    assert isinstance(text, six.binary_type)
    assert text.decode('utf-8') == 'hello ❤'

    # ascii returns utf-8
    text = terminal.clean('hello'.encode('ascii'))
    assert isinstance(text, six.binary_type)
    assert text.decode('utf-8') == 'hello'


def test_terminal_clean_ncols(terminal):

    text = terminal.clean('hello', n_cols=5)
    assert text.decode('utf-8') == 'hello'

    text = terminal.clean('hello', n_cols=4)
    assert text.decode('utf-8') == 'hell'

    text = terminal.clean('ｈｅｌｌｏ', n_cols=10)
    assert text.decode('utf-8') == 'ｈｅｌｌｏ'

    text = terminal.clean('ｈｅｌｌｏ', n_cols=9)
    assert text.decode('utf-8') == 'ｈｅｌｌ'


@pytest.mark.parametrize('use_ascii', [True, False])
def test_terminal_clean_unescape_html(terminal, use_ascii):

    # HTML characters get decoded
    terminal.config['ascii'] = use_ascii
    text = terminal.clean('&lt;')
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii' if use_ascii else 'utf-8') == '<'


@pytest.mark.parametrize('use_ascii', [True, False])
def test_terminal_add_line(terminal, stdscr, use_ascii):

    terminal.config['ascii'] = use_ascii

    terminal.add_line(stdscr, 'hello')
    assert stdscr.addstr.called_with(0, 0, 'hello'.encode('ascii'))
    stdscr.reset_mock()

    # Text will be drawn, but cut off to fit on the screen
    terminal.add_line(stdscr, 'hello', row=3, col=75)
    assert stdscr.addstr.called_with((3, 75, 'hell'.encode('ascii')))
    stdscr.reset_mock()

    # Outside of screen bounds, don't even try to draw the text
    terminal.add_line(stdscr, 'hello', col=79)
    assert not stdscr.addstr.called
    stdscr.reset_mock()


@pytest.mark.parametrize('use_ascii', [True, False])
def test_terminal_show_notification(terminal, stdscr, use_ascii):

    terminal.config['ascii'] = use_ascii

    # Multi-line messages should be automatically split
    text = 'line 1\nline 2\nline3'
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == 5
    assert stdscr.subwin.addstr.call_count == 3
    stdscr.reset_mock()

    # The text should be trimmed to fit 40x80
    text = HELP.strip().splitlines()
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == 40
    assert stdscr.subwin.ncols <= 80
    assert stdscr.subwin.addstr.call_count == 38
    stdscr.reset_mock()

    # The text should be trimmed to fit in 20x20
    stdscr.nlines, stdscr.ncols = 15, 20
    text = HELP.strip().splitlines()
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == 15
    assert stdscr.subwin.ncols == 20
    assert stdscr.subwin.addstr.call_count == 13


@pytest.mark.parametrize('use_ascii', [True, False])
def test_terminal_text_input(terminal, stdscr, use_ascii):

    terminal.config['ascii'] = use_ascii
    stdscr.nlines = 1

    # Text will be wrong because stdscr.inch() is not implemented
    # But we can at least tell if text was captured or not
    stdscr.getch.side_effect = [ord('h'), ord('i'), ord('!'), terminal.RETURN]
    assert isinstance(terminal.text_input(stdscr), six.text_type)

    stdscr.getch.side_effect = [ord('b'), ord('y'), ord('e'), terminal.ESCAPE]
    assert terminal.text_input(stdscr) is None

    stdscr.getch.side_effect = [ord('h'), curses.KEY_RESIZE, terminal.RETURN]
    assert terminal.text_input(stdscr, allow_resize=True) is not None

    stdscr.getch.side_effect = [ord('h'), curses.KEY_RESIZE, terminal.RETURN]
    assert terminal.text_input(stdscr, allow_resize=False) is None


@pytest.mark.parametrize('use_ascii', [True, False])
def test_terminal_prompt_input(terminal, stdscr, use_ascii):

    terminal.config['ascii'] = use_ascii
    window = stdscr.derwin()

    window.getch.side_effect = [ord('h'), ord('i'), terminal.RETURN]
    assert isinstance(terminal.prompt_input('hi'), six.text_type)

    stdscr.subwin.addstr.assert_called_with(0, 0, 'hi'.encode('ascii'))
    assert window.nlines == 1
    assert window.ncols == 78

    window.getch.side_effect = [ord('b'), ord('y'), ord('e'), terminal.ESCAPE]
    assert terminal.prompt_input('hi') is None

    stdscr.getch.side_effect = [ord('b'), ord('e'), terminal.RETURN]
    assert terminal.prompt_input('hi', key=True) == ord('b')

    stdscr.getch.side_effect = [terminal.ESCAPE, ord('e'), ord('l')]
    assert terminal.prompt_input('hi', key=True) is None


def test_terminal_prompt_y_or_n(terminal, stdscr):

    stdscr.getch.side_effect = [ord('y'), ord('N'), terminal.ESCAPE, ord('a')]
    text = 'hi'.encode('ascii')

    # Press 'y'
    assert terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text)
    assert not curses.flash.called

    # Press 'N'
    assert not terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text)
    assert not curses.flash.called

    # Press Esc
    assert not terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text)
    assert not curses.flash.called

    # Press an invalid key
    assert not terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text)
    assert curses.flash.called


@pytest.mark.parametrize('use_ascii', [True, False])
def test_terminal_open_editor(terminal, use_ascii):

    terminal.config['ascii'] = use_ascii

    comment = COMMENT_EDIT_FILE.format(id=1, content='Comment 1 ❤')
    data = {'filename': None}

    def side_effect(args):
        data['filename'] = args[1]
        with codecs.open(data['filename'], 'r+', 'utf-8') as fp:
            assert fp.read() == comment
            fp.write('Comment 2 ❤')
        return mock.Mock()

    with mock.patch('subprocess.Popen', autospec=True) as Popen:
        Popen.side_effect = side_effect

        with terminal.open_editor(comment) as reply_text:
            assert reply_text == 'Comment 1 ❤\nComment 2 ❤'
            assert os.path.isfile(data['filename'])
            assert curses.endwin.called
            assert curses.doupdate.called
        assert not os.path.isfile(data['filename'])


def test_terminal_open_editor_error(terminal):

    with mock.patch('subprocess.Popen', autospec=True) as Popen, \
            mock.patch.object(terminal, 'show_notification'):

        # Invalid editor
        Popen.side_effect = OSError
        with terminal.open_editor('hello') as text:
            assert text == 'hello'
        assert 'Could not open' in terminal.show_notification.call_args[0][0]

        data = {'filename': None}

        def side_effect(args):
            data['filename'] = args[1]
            return mock.Mock()

        # Temporary File Errors don't delete the file
        Popen.side_effect = side_effect
        with terminal.open_editor('test'):
            assert os.path.isfile(data['filename'])
            raise TemporaryFileError()
        assert os.path.isfile(data['filename'])
        os.remove(data['filename'])

        # Other Exceptions don't delete the file *and* are propagated
        Popen.side_effect = side_effect
        with pytest.raises(ValueError):
            with terminal.open_editor('test'):
                assert os.path.isfile(data['filename'])
                raise ValueError()
        assert os.path.isfile(data['filename'])
        os.remove(data['filename'])

        # Gracefully handle the case when we can't remove the file
        with mock.patch.object(os, 'remove'):
            os.remove.side_effect = OSError
            with terminal.open_editor():
                pass
            assert os.remove.called

        assert os.path.isfile(data['filename'])
        os.remove(data['filename'])


def test_terminal_open_link_mailcap(terminal):

    url = 'http://www.test.com'

    class MockMimeParser(object):
        pattern = re.compile('')

    mock_mime_parser = MockMimeParser()

    with mock.patch.object(terminal, 'open_browser'), \
            mock.patch('rtv.terminal.mime_parsers') as mime_parsers:
        mime_parsers.parsers = [mock_mime_parser]

        # Pass through to open_browser if media is disabled
        terminal.config['enable_media'] = False
        terminal.open_link(url)
        assert terminal.open_browser.called
        terminal.open_browser.reset_mock()

        # Invalid content type
        terminal.config['enable_media'] = True
        mock_mime_parser.get_mimetype = lambda url: (url, None)
        terminal.open_link(url)
        assert terminal.open_browser.called
        terminal.open_browser.reset_mock()

        # Text/html defers to open_browser
        mock_mime_parser.get_mimetype = lambda url: (url, 'text/html')
        terminal.open_link(url)
        assert terminal.open_browser.called
        terminal.open_browser.reset_mock()


def test_terminal_open_link_subprocess(terminal):

    url = 'http://www.test.com'
    terminal.config['enable_media'] = True

    with mock.patch('time.sleep'),                            \
            mock.patch('os.system'),                          \
            mock.patch('subprocess.Popen') as Popen,          \
            mock.patch('six.moves.input') as six_input,       \
            mock.patch.object(terminal, 'get_mailcap_entry'):

        six_input.return_values = 'y'

        def reset_mock():
            six_input.reset_mock()
            os.system.reset_mock()
            terminal.stdscr.subwin.addstr.reset_mock()
            Popen.return_value.communicate.return_value = '', 'stderr message'
            Popen.return_value.poll.return_value = 0
            Popen.return_value.wait.return_value = 0

        def get_error():
            # Check if an error message was printed to the terminal
            status = 'Program exited with status'.encode('utf-8')
            return any(status in args[0][2] for args in
                       terminal.stdscr.subwin.addstr.call_args_list)

        # Non-blocking success
        reset_mock()
        entry = ('echo ""', 'echo %s')
        terminal.get_mailcap_entry.return_value = entry
        terminal.open_link(url)
        assert not six_input.called
        assert not get_error()

        # Non-blocking failure
        reset_mock()
        Popen.return_value.poll.return_value = 127
        Popen.return_value.wait.return_value = 127
        entry = ('fake .', 'fake %s')
        terminal.get_mailcap_entry.return_value = entry
        terminal.open_link(url)
        assert not six_input.called
        assert get_error()

        # needsterminal success
        reset_mock()
        entry = ('echo ""', 'echo %s; needsterminal')
        terminal.get_mailcap_entry.return_value = entry
        terminal.open_link(url)
        assert not six_input.called
        assert not get_error()

        # needsterminal failure
        reset_mock()
        Popen.return_value.poll.return_value = 127
        Popen.return_value.wait.return_value = 127
        entry = ('fake .', 'fake %s; needsterminal')
        terminal.get_mailcap_entry.return_value = entry
        terminal.open_link(url)
        assert not six_input.called
        assert get_error()

        # copiousoutput success
        reset_mock()
        entry = ('echo ""', 'echo %s; needsterminal; copiousoutput')
        terminal.get_mailcap_entry.return_value = entry
        terminal.open_link(url)
        assert six_input.called
        assert not get_error()

        # copiousoutput failure
        reset_mock()
        Popen.return_value.poll.return_value = 127
        Popen.return_value.wait.return_value = 127
        entry = ('fake .', 'fake %s; needsterminal; copiousoutput')
        terminal.get_mailcap_entry.return_value = entry
        terminal.open_link(url)
        assert six_input.called
        assert get_error()


def test_terminal_open_browser_display(terminal):

    terminal._display = True
    with mock.patch('webbrowser.open_new_tab', autospec=True) as open_new_tab:
        terminal.open_browser('http://www.test.com')

    # open_new_tab() will be executed in the child process so we can't
    # directly check if the was called from here or not.
    # open_new_tab.assert_called_with('http://www.test.com')

    # Shouldn't suspend curses
    assert not curses.endwin.called
    assert not curses.doupdate.called


def test_terminal_open_browser_display_no_response(terminal):

    terminal._display = True
    with mock.patch('rtv.terminal.Process', autospec=True) as Process:
        Process.return_value.is_alive.return_value = 1
        terminal.open_browser('http://www.test.com')
    assert isinstance(terminal.loader.exception, BrowserError)


def test_terminal_open_browser_no_display(terminal):

    terminal._display = False
    with mock.patch('webbrowser.open_new_tab', autospec=True) as open_new_tab:
        terminal.open_browser('http://www.test.com')
    open_new_tab.assert_called_with('http://www.test.com')

    # Should suspend curses to give control of the terminal to the browser
    assert curses.endwin.called
    assert curses.doupdate.called


def test_terminal_open_pager(terminal, stdscr):

    data = "Hello World!  ❤"

    def side_effect(args, stdin=None):
        assert stdin is not None
        raise OSError

    with mock.patch('subprocess.Popen', autospec=True) as Popen, \
            mock.patch.dict('os.environ', {'PAGER': 'fake'}):
        Popen.return_value.stdin = mock.Mock()

        terminal.open_pager(data)
        assert Popen.called
        assert not stdscr.addstr.called

        # Raise an OS error
        Popen.side_effect = side_effect
        terminal.open_pager(data)
        message = 'Could not open pager fake'.encode('ascii')
        assert stdscr.addstr.called_with(0, 0, message)


def test_terminal_open_urlview(terminal, stdscr):

    data = "Hello World!  ❤"

    def side_effect(args, stdin=None):
        assert stdin is not None
        raise OSError

    with mock.patch('subprocess.Popen') as Popen, \
            mock.patch.dict('os.environ', {'RTV_URLVIEWER': 'fake'}):

        Popen.return_value.poll.return_value = 0
        terminal.open_urlview(data)
        assert Popen.called
        assert not stdscr.addstr.called

        Popen.return_value.poll.return_value = 1
        terminal.open_urlview(data)
        assert stdscr.subwin.addstr.called

        # Raise an OS error
        Popen.side_effect = side_effect
        terminal.open_urlview(data)
        message = 'Failed to open fake'.encode('utf-8')
        assert stdscr.addstr.called_with(0, 0, message)


def test_terminal_strip_textpad(terminal):

    assert terminal.strip_textpad(None) is None
    assert terminal.strip_textpad('  foo  ') == '  foo'

    text = 'alpha bravo\ncharlie \ndelta  \n  echo   \n\nfoxtrot\n\n\n'
    assert terminal.strip_textpad(text) == (
        'alpha bravocharlie delta\n  echo\n\nfoxtrot')


def test_terminal_add_space(terminal, stdscr):

    stdscr.x, stdscr.y = 10, 20
    terminal.add_space(stdscr)
    stdscr.addstr.assert_called_with(20, 10, ' ')

    # Not enough room to add a space
    stdscr.reset_mock()
    stdscr.x = 10
    stdscr.ncols = 11
    terminal.add_space(stdscr)
    assert not stdscr.addstr.called


def test_terminal_attr(terminal):

    assert terminal.attr('CursorBlock') == 0
    assert terminal.attr('@CursorBlock') == curses.A_REVERSE
    assert terminal.attr('NeutralVote') == curses.A_BOLD

    with terminal.theme.turn_on_selected():
        assert terminal.attr('CursorBlock') == curses.A_REVERSE
        assert terminal.attr('NeutralVote') == curses.A_BOLD


def test_terminal_check_theme(terminal):

    monochrome = Theme(use_color=False)
    default = Theme()
    color256 = Theme.from_name('molokai')

    curses.has_colors.return_value = False
    assert terminal.check_theme(monochrome)
    assert not terminal.check_theme(default)
    assert not terminal.check_theme(color256)

    curses.has_colors.return_value = True
    curses.COLORS = 0
    assert terminal.check_theme(monochrome)
    assert not terminal.check_theme(default)
    assert not terminal.check_theme(color256)

    curses.COLORS = 8
    assert terminal.check_theme(monochrome)
    assert terminal.check_theme(default)
    assert not terminal.check_theme(color256)

    curses.COLORS = 256
    assert terminal.check_theme(monochrome)
    assert terminal.check_theme(default)
    assert terminal.check_theme(color256)

    curses.COLOR_PAIRS = 8
    assert terminal.check_theme(monochrome)
    assert terminal.check_theme(default)
    assert not terminal.check_theme(color256)


def test_terminal_set_theme(terminal, stdscr):

    # Default with color enabled
    stdscr.reset_mock()
    terminal.set_theme()
    assert terminal.theme.use_color
    assert terminal.theme.display_string == 'default (built-in)'
    stdscr.bkgd.assert_called_once_with(' ', 0)

    # When the user passes in the --monochrome flag
    terminal.theme = None
    terminal.set_theme(Theme(use_color=False))
    assert not terminal.theme.use_color
    assert terminal.theme.display_string == 'monochrome (built-in)'

    # When the terminal doesn't support colors
    curses.COLORS = 0
    terminal.theme = None
    terminal.set_theme()
    assert terminal.theme.display_string == 'monochrome (built-in)'

    # When the terminal doesn't support 256 colors so it falls back to the
    # built-in default theme
    curses.COLORS = 8
    terminal.theme = None
    terminal.set_theme(Theme.from_name('molokai'))
    assert terminal.theme.display_string == 'default (built-in)'

    # When the terminal does support the 256 color theme
    curses.COLORS = 256
    terminal.theme = None
    terminal.set_theme(Theme.from_name('molokai'))
    assert terminal.theme.display_string == 'molokai (preset)'


def test_terminal_set_theme_no_colors(terminal, stdscr):

    # Monochrome should be forced if the terminal doesn't support color
    with mock.patch('curses.has_colors') as has_colors:
        has_colors.return_value = False

        terminal.set_theme()
        assert not terminal.theme.use_color

        terminal.set_theme(Theme(use_color=True))
        assert not terminal.theme.use_color


def test_terminal_strip_instructions(terminal):

    # These templates only contain instructions, so they should be empty
    assert terminal.strip_instructions(SUBMISSION_FILE) == ''
    assert terminal.strip_instructions(REPLY_FILE) == ''
    assert terminal.strip_instructions(MESSAGE_FILE) == ''

    # These templates should strip everything but the {content} tag,
    # which will be replaced with the submission/content to be edited
    assert terminal.strip_instructions(SUBMISSION_EDIT_FILE) == '{content}'
    assert terminal.strip_instructions(COMMENT_EDIT_FILE) == '{content}'

    # Comments without the INSTRUCTIONS marker shouldn't be stripped
    text = '<!-- A normal HTML comment -->'
    assert terminal.strip_instructions(text) == text

    # Hashes shouldn't be stripped anymore
    text = '# This is no longer interpreted as a comment!'
    assert terminal.strip_instructions(text) == text

    # Nested HTML comment tags shouldn't be shown
    text = '<!--{0} <!-- A nested HTML comment --> {0}-->'.format(TOKEN)
    assert terminal.strip_instructions(text) == ''

    # Another edge case
    text = '<!--{0} instructions {0}--><!-- An HTML comment -->'.format(TOKEN)
    assert terminal.strip_instructions(text) == '<!-- An HTML comment -->'

    # Whitespace at the start of the first line should be preserved
    text = '    code\n    block\n'
    assert terminal.strip_instructions(text) == '    code\n    block'

    # But blank lines should be stripped
    text = '\n    \n    code\n    block\n'
    assert terminal.strip_instructions(text) == '    code\n    block'

    # However, blank lines in the middle of comment should not be stripped
    text = 'paragraph 1\n\nparagraph 2\n'
    assert terminal.strip_instructions(text) == 'paragraph 1\n\nparagraph 2'


def test_terminal_get_link_pages(terminal):

    # When there are no links passed in, there should be no pages generated
    assert terminal.get_link_pages([]) == []

    # A single link should generate a single page
    assert terminal.get_link_pages([1]) == [[1]]

    # Up to 10 links should fit on a single page
    link_pages = terminal.get_link_pages([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert link_pages == [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

    # When the 11th link is added a new page is created
    link_pages = terminal.get_link_pages([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert link_pages == [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [10]]


def test_terminal_get_link_page_text(terminal):

    link_page = [
        {'href': 'https://www.reddit.com', 'text': 'Reddit Homepage'},
        {'href': 'https://www.duckduckgo.com', 'text': 'Search Engine'},
        {
            'href': 'https://github.com/michael-lazar/rtv',
            'text': 'This project\'s homepage'
        }
    ]

    text = terminal.get_link_page_text(link_page)
    assert text == dedent("""\
    [0] [Reddit Homepage](https://www.reddit.com)
    [1] [Search Engine](https://www.duckduckgo.com)
    [2] [This project's home…](https://github.com/michael-lazar/rtv)
    """)


def test_terminal_prompt_user_to_select_link(terminal, stdscr):

    # Select the 2nd link on the 2nd page
    links = [
        {'href': 'www.website-0.com', 'text': 'Website 0'},
        {'href': 'www.website-1.com', 'text': 'Website 1'},
        {'href': 'www.website-2.com', 'text': 'Website 2'},
        {'href': 'www.website-3.com', 'text': 'Website 3'},
        {'href': 'www.website-4.com', 'text': 'Website 4'},
        {'href': 'www.website-5.com', 'text': 'Website 5'},
        {'href': 'www.website-6.com', 'text': 'Website 6'},
        {'href': 'www.website-7.com', 'text': 'Website 7'},
        {'href': 'www.website-8.com', 'text': 'Website 8'},
        {'href': 'www.website-9.com', 'text': 'Website 9'},
        {'href': 'www.website-10.com', 'text': 'Website 10'},
        {'href': 'www.website-11.com', 'text': 'Website 11'},
        {'href': 'www.website-12.com', 'text': 'Website 12'},
    ]
    stdscr.getch.side_effect = [ord('j'), ord('2')]
    href = terminal.prompt_user_to_select_link(links)
    assert href == 'www.website-12.com'

    # Select a link that doesn't exist
    links = [
        {'href': 'www.website-0.com', 'text': 'Website 0'},
        {'href': 'www.website-1.com', 'text': 'Website 1'},
        {'href': 'www.website-2.com', 'text': 'Website 2'},
    ]
    stdscr.getch.side_effect = [ord('3')]
    assert terminal.prompt_user_to_select_link(links) is None

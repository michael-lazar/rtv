# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import curses
import codecs

import six
import pytest

from rtv.docs import HELP, COMMENT_EDIT_FILE
from rtv.objects import Color
from rtv.exceptions import TemporaryFileError

try:
    from unittest import mock
except ImportError:
    import mock


def test_terminal_properties(terminal, config):

    assert len(terminal.up_arrow) == 2
    assert isinstance(terminal.up_arrow[0], six.text_type)
    assert len(terminal.down_arrow) == 2
    assert isinstance(terminal.down_arrow[0], six.text_type)
    assert len(terminal.neutral_arrow) == 2
    assert isinstance(terminal.neutral_arrow[0], six.text_type)
    assert len(terminal.guilded) == 2
    assert isinstance(terminal.guilded[0], six.text_type)

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': ''}):
        assert terminal.display is False

    terminal._display = None
    with mock.patch('rtv.terminal.sys') as sys, \
            mock.patch.dict('os.environ', {'DISPLAY': ''}):
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
    assert terminal.ascii == config['ascii']
    assert terminal.loader is not None

    assert terminal.MIN_HEIGHT is not None
    assert terminal.MIN_WIDTH is not None


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


def test_terminal_clean_ascii(terminal):

    terminal.ascii = True

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

    terminal.ascii = False

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


@pytest.mark.parametrize('ascii', [True, False])
def test_terminal_clean_unescape_html(terminal, ascii):

    # HTML characters get decoded
    terminal.ascii = ascii
    text = terminal.clean('&lt;')
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii' if ascii else 'utf-8') == '<'


@pytest.mark.parametrize('ascii', [True, False])
def test_terminal_add_line(terminal, stdscr, ascii):

    terminal.ascii = ascii

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


@pytest.mark.parametrize('ascii', [True, False])
def test_show_notification(terminal, stdscr, ascii):

    terminal.ascii = ascii

    # The whole message should fit in 40x80
    text = HELP.strip().splitlines()
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == len(text) + 2
    assert stdscr.subwin.ncols == 80
    assert stdscr.subwin.addstr.call_count == len(text)
    stdscr.reset_mock()

    # The text should be trimmed to fit in 20x20
    stdscr.nlines, stdscr.ncols = 15, 20
    text = HELP.strip().splitlines()
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == 15
    assert stdscr.subwin.ncols == 20
    assert stdscr.subwin.addstr.call_count == 13


@pytest.mark.parametrize('ascii', [True, False])
def test_text_input(terminal, stdscr, ascii):

    terminal.ascii = ascii
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


@pytest.mark.parametrize('ascii', [True, False])
def test_prompt_input(terminal, stdscr, ascii):

    terminal.ascii = ascii
    window = stdscr.derwin()

    window.getch.side_effect = [ord('h'), ord('i'), terminal.RETURN]
    assert isinstance(terminal.prompt_input('hi'), six.text_type)

    attr = Color.CYAN | curses.A_BOLD
    stdscr.subwin.addstr.assert_called_with(0, 0, 'hi'.encode('ascii'), attr)
    assert window.nlines == 1
    assert window.ncols == 78

    window.getch.side_effect = [ord('b'), ord('y'), ord('e'), terminal.ESCAPE]
    assert terminal.prompt_input('hi') is None

    stdscr.getch.side_effect = [ord('b'), ord('e'), terminal.RETURN]
    assert terminal.prompt_input('hi', key=True) == ord('b')

    stdscr.getch.side_effect = [terminal.ESCAPE, ord('e'), ord('l')]
    assert terminal.prompt_input('hi', key=True) is None


def test_prompt_y_or_n(terminal, stdscr):

    stdscr.getch.side_effect = [ord('y'), ord('N'), terminal.ESCAPE, ord('a')]
    attr = Color.CYAN | curses.A_BOLD
    text = 'hi'.encode('ascii')

    # Press 'y'
    assert terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text, attr)
    assert not curses.flash.called

    # Press 'N'
    assert not terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text, attr)
    assert not curses.flash.called

    # Press Esc
    assert not terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text, attr)
    assert not curses.flash.called

    # Press an invalid key
    assert not terminal.prompt_y_or_n('hi')
    stdscr.subwin.addstr.assert_called_with(0, 0, text, attr)
    assert curses.flash.called


@pytest.mark.parametrize('ascii', [True, False])
def test_open_editor(terminal, ascii):

    terminal.ascii = ascii

    comment = COMMENT_EDIT_FILE.format(content='#| This is a comment! ❤')
    data = {'filename': None}

    def side_effect(args):
        data['filename'] = args[1]
        with codecs.open(data['filename'], 'r+', 'utf-8') as fp:
            assert fp.read() == comment
            fp.write('This is an amended comment! ❤')
        return mock.Mock()

    with mock.patch('subprocess.Popen', autospec=True) as Popen:
        Popen.side_effect = side_effect

        with terminal.open_editor(comment) as reply_text:
            assert reply_text == 'This is an amended comment! ❤'
            assert os.path.isfile(data['filename'])
            assert curses.endwin.called
            assert curses.doupdate.called
        assert not os.path.isfile(data['filename'])


def test_open_editor_error(terminal):

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


def test_open_browser(terminal):

    url = 'http://www.test.com'

    terminal._display = True
    with mock.patch('subprocess.Popen', autospec=True) as Popen:
        Popen.return_value.poll.return_value = 0
        terminal.open_browser(url)
    assert Popen.called
    assert not curses.endwin.called
    assert not curses.doupdate.called

    terminal._display = False
    with mock.patch('webbrowser.open_new_tab', autospec=True) as open_new_tab:
        terminal.open_browser(url)
    open_new_tab.assert_called_with(url)
    assert curses.endwin.called
    assert curses.doupdate.called


def test_open_pager(terminal, stdscr):

    data = "Hello World!"

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
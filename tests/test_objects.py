# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

import pytest
import requests

from rtv.objects import Color, Controller, Navigator, curses_session

try:
    from unittest import mock
except ImportError:
    import mock


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Ensure the thread is properly started/stopped
    with terminal.loader(delay=0, message=u'Hello', trail=u'...'):
        assert terminal.loader._animator.is_alive()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert terminal.loader.exception is None
    assert stdscr.subwin.ncols == 10
    assert stdscr.subwin.nlines == 3


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_exception_unhandled(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Raising an exception should clean up the loader properly
    with pytest.raises(Exception):
        with terminal.loader(delay=0):
            assert terminal.loader._animator.is_alive()
            raise Exception()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_exception_handled(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Raising a handled exception should get stored on the loaders
    with terminal.loader(delay=0):
        assert terminal.loader._animator.is_alive()
        raise requests.ConnectionError()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert isinstance(terminal.loader.exception, requests.ConnectionError)
    error_message = 'Connection Error'.encode('ascii' if ascii else 'utf-8')
    stdscr.subwin.addstr.assert_called_with(1, 1, error_message)


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_exception_not_caught(terminal, stdscr, ascii):
    terminal.ascii = ascii

    with pytest.raises(KeyboardInterrupt):
        with terminal.loader(delay=0, catch_exception=False):
            assert terminal.loader._animator.is_alive()
            raise KeyboardInterrupt()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert terminal.loader.exception is None


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_keyboard_interrupt(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Raising a KeyboardInterrupt should be also be stored
    with terminal.loader(delay=0):
        assert terminal.loader._animator.is_alive()
        raise KeyboardInterrupt()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert isinstance(terminal.loader.exception, KeyboardInterrupt)


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_escape(terminal, stdscr, ascii):
    terminal.ascii = ascii

    stdscr.getch.return_value = terminal.ESCAPE

    # Pressing escape should trigger an interrupt during the delay section
    with mock.patch('os.kill') as kill:
        with terminal.loader():
            time.sleep(0.1)
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert kill.called

    # As will as during the animation section
    with mock.patch('os.kill') as kill:
        with terminal.loader(delay=0):
            time.sleep(0.1)
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert kill.called


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_initial_delay(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # If we don't reach the initial delay nothing should be drawn
    with terminal.loader(delay=0.1):
        time.sleep(0.05)
    assert not stdscr.subwin.addstr.called


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_nested(terminal, ascii):
    terminal.ascii = ascii

    with terminal.loader(message='Outer'):
        with terminal.loader(message='Inner'):
            raise requests.ConnectionError()
        assert False  # Should never be reached

    assert isinstance(terminal.loader.exception, requests.ConnectionError)
    assert terminal.loader.depth == 0
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()


@pytest.mark.parametrize('ascii', [True, False])
def test_objects_load_screen_nested_complex(terminal, stdscr, ascii):
    terminal.ascii = ascii

    with terminal.loader(message='Outer') as outer_loader:
        assert outer_loader.depth == 1

        with terminal.loader(message='Inner') as inner_loader:
            assert inner_loader.depth == 2
            assert inner_loader._args[2] == 'Outer'

        with terminal.loader():
            assert terminal.loader.depth == 2
            raise requests.ConnectionError()

        assert False  # Should never be reached

    assert isinstance(terminal.loader.exception, requests.ConnectionError)
    assert terminal.loader.depth == 0
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    error_message = 'Connection Error'.encode('ascii' if ascii else 'utf-8')
    stdscr.subwin.addstr.assert_called_once_with(1, 1, error_message)


def test_objects_color(stdscr):

    colors = ['RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE']

    # Check that all colors start with the default value
    for color in colors:
        assert getattr(Color, color) == curses.A_NORMAL

    Color.init()
    assert curses.use_default_colors.called

    # Check that all colors are populated
    for color in colors:
        assert getattr(Color, color) == 23


def test_objects_curses_session(stdscr):

    # Normal setup and cleanup
    with curses_session():
        pass
    assert curses.initscr.called
    assert curses.endwin.called
    curses.initscr.reset_mock()
    curses.endwin.reset_mock()

    # Ensure cleanup runs if an error occurs
    with pytest.raises(KeyboardInterrupt):
        with curses_session():
            raise KeyboardInterrupt()
    assert curses.initscr.called
    assert curses.endwin.called
    curses.initscr.reset_mock()
    curses.endwin.reset_mock()

    # But cleanup shouldn't run if stdscr was never instantiated
    curses.initscr.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        with curses_session():
            pass
    assert curses.initscr.called
    assert not curses.endwin.called
    curses.initscr.reset_mock()
    curses.endwin.reset_mock()


def test_objects_controller():

    class ControllerA(Controller):
        character_map = {}

    class ControllerB(ControllerA):
        character_map = {}

    class ControllerC(ControllerA):
        character_map = {}

    @ControllerA.register('1')
    def call_page(_):
        return 'a1'

    @ControllerA.register('2')
    def call_page(_):
        return 'a2'

    @ControllerB.register('1')
    def call_page(_):
        return 'b1'

    @ControllerC.register('2')
    def call_page(_):
        return 'c2'

    controller_a = ControllerA(None)
    controller_b = ControllerB(None)
    controller_c = ControllerC(None)

    assert controller_a.trigger('1') == 'a1'
    assert controller_a.trigger('2') == 'a2'
    assert controller_a.trigger('3') is None

    assert controller_b.trigger('1') == 'b1'
    assert controller_b.trigger('2') == 'a2'
    assert controller_b.trigger('3') is None

    assert controller_c.trigger('1') == 'a1'
    assert controller_c.trigger('2') == 'c2'
    assert controller_c.trigger('3') is None


def test_objects_navigator_properties():

    def valid_page_cb(_):
        return

    nav = Navigator(valid_page_cb)
    assert nav.step == 1
    assert nav.position == (0, 0, False)
    assert nav.absolute_index == 0

    nav = Navigator(valid_page_cb, 5, 2, True)
    assert nav.step == -1
    assert nav.position == (5, 2, True)
    assert nav.absolute_index == 3


def test_objects_navigator_move():

    def valid_page_cb(index):
        if index < 0 or index > 3:
            raise IndexError()

    nav = Navigator(valid_page_cb)

    # Try to scroll up past the first item
    valid, redraw = nav.move(-1, 2)
    assert not valid
    assert not redraw

    # Scroll down
    valid, redraw = nav.move(1, 3)
    assert nav.page_index == 0
    assert nav.cursor_index == 1
    assert valid
    assert not redraw

    # Scroll down, reach last item on the page and flip the screen
    valid, redraw = nav.move(1, 3)
    assert nav.page_index == 2
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Keep scrolling
    valid, redraw = nav.move(1, 3)
    assert nav.page_index == 3
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Reach the end of the page and stop
    valid, redraw = nav.move(1, 1)
    assert nav.page_index == 3
    assert nav.cursor_index == 0
    assert nav.inverted
    assert not valid
    assert not redraw

    # Last item was large and takes up the whole screen, scroll back up and
    # flip the screen again
    valid, redraw = nav.move(-1, 1)
    assert nav.page_index == 2
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw


def test_objects_navigator_move_new_submission():

    def valid_page_cb(index):
        if index != -1:
            raise IndexError()

    nav = Navigator(valid_page_cb, page_index=-1)

    # Can't move up
    valid, redraw = nav.move(-1, 1)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw

    # Can't move down
    valid, redraw = nav.move(1, 1)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw


def test_objects_navigator_move_submission():

    def valid_page_cb(index):
        if index < -1 or index > 4:
            raise IndexError()

    nav = Navigator(valid_page_cb, page_index=-1)

    # Can't move up
    valid, redraw = nav.move(-1, 2)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw

    # Moving down jumps to the first comment
    valid, redraw = nav.move(1, 2)
    assert nav.page_index == 0
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw

    # Moving down again inverts the screen
    valid, redraw = nav.move(1, 2)
    assert nav.page_index == 1
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Move up to the first comment
    valid, redraw = nav.move(-1, 2)
    assert nav.page_index == 0
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw

    # Move up to the submission
    valid, redraw = nav.move(-1, 2)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw


@pytest.mark.xfail(reason="Paging is still broken in several edge-cases")
def test_objects_navigator_move_page():

    def valid_page_cb(index):
        if index < 0 or index > 7:
            raise IndexError()

    nav = Navigator(valid_page_cb, cursor_index=2)

    # Can't move up
    valid, redraw = nav.move_page(-1, 5)
    assert nav.page_index == 0
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw

    # Page down
    valid, redraw = nav.move_page(1, 5)
    assert nav.page_index == 4
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Page up
    valid, redraw = nav.move_page(-1, 3)
    assert nav.page_index == 2
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw


def test_objects_navigator_flip():

    def valid_page_cb(index):
        if index < 0 or index > 10:
            raise IndexError()

    nav = Navigator(valid_page_cb)

    nav.flip(5)
    assert nav.page_index == 5
    assert nav.cursor_index == 5
    assert nav.inverted

    nav.flip(3)
    assert nav.page_index == 2
    assert nav.cursor_index == 3
    assert not nav.inverted
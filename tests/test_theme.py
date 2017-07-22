import os
import curses
from collections import OrderedDict
from tempfile import NamedTemporaryFile

import pytest


from rtv.theme import Theme
from rtv.config import DEFAULT_THEMES
from rtv.exceptions import ConfigError

try:
    from unittest import mock
except ImportError:
    import mock


INVALID_ELEMENTS = OrderedDict([
    ('too_few_items', 'upvote = blue\n'),
    ('too_many_items', 'upvote = blue blue bold underline\n'),
    ('invalid_fg', 'upvote = invalid blue\n'),
    ('invalid_bg', 'upvote = blue invalid\n'),
    ('invalid_attr', 'upvote = blue blue bold+invalid\n'),
    ('invalid_hex', 'upvote = #fffff blue\n'),
    ('invalid_hex2', 'upvote = #gggggg blue\n'),
    ('out_of_range', 'upvote = ansi_256 blue\n')
])


def test_theme_construct():

    theme = Theme()
    assert theme.name == 'default'
    assert theme.elements == Theme.DEFAULT_THEME
    assert theme.required_colors == 8
    assert theme.required_color_pairs == 6

    theme = Theme(name='monochrome', monochrome=True)
    assert theme.name == 'monochrome'
    assert theme.monochrome is True
    assert theme.required_colors == 0
    assert theme.required_color_pairs == 0

    elements = {'bar_level_1': (100, 101, curses.A_UNDERLINE)}
    theme = Theme(elements=elements)
    assert theme.elements['bar_level_1'] == elements['bar_level_1']
    assert theme.required_colors == 256


def test_theme_default_cfg_matches_builtin():

    filename = os.path.join(DEFAULT_THEMES, 'default.cfg')
    default_theme = Theme.from_file(filename)

    # The default theme file should match the hardcoded values
    assert default_theme.elements == Theme().elements

    class MockTheme(Theme):
        def __init__(self, name=None, elements=None, monochrome=False):
            assert name == 'default'
            assert elements == Theme.DEFAULT_THEME
            assert monochrome is False

    # Make sure that the config file elements exactly match the defaults
    MockTheme.from_file(filename)


args, ids = INVALID_ELEMENTS.values(), list(INVALID_ELEMENTS)
@pytest.mark.parametrize('line', args, ids=ids)
def test_theme_from_file_invalid(line):

    with NamedTemporaryFile(mode='w+') as fp:
        fp.write('[theme]\n')
        fp.write(line)
        fp.flush()
        with pytest.raises(ConfigError):
            Theme.from_file(fp.name)


def test_theme_from_file():

    with NamedTemporaryFile(mode='w+') as fp:

        # Needs a [theme] section
        with pytest.raises(ConfigError):
            Theme.from_file(fp.name)

        fp.write('[theme]\n')
        fp.write('unknown = neutral neutral\n')
        fp.write('upvote = default red\n')
        fp.write('downvote = ansi_0 ansi_255 bold\n')
        fp.write('neutral_vote = #000000 #ffffff bold+reverse\n')
        fp.flush()

        theme = Theme.from_file(fp.name)
        assert 'unknown' not in theme.elements
        assert theme.elements['upvote'] == (
            -1, curses.COLOR_RED, curses.A_NORMAL)
        assert theme.elements['downvote'] == (
            0, 255, curses.A_BOLD)
        assert theme.elements['neutral_vote'] == (
            16, 231, curses.A_BOLD | curses.A_REVERSE)


def test_theme_from_name():

    with NamedTemporaryFile(mode='w+', suffix='.cfg') as fp:
        path, filename = os.path.split(fp.name)
        theme_name = filename[:-4]

        fp.write('[theme]\n')
        fp.write('upvote = default default\n')
        fp.flush()

        # Full file path
        theme = Theme.from_name(fp.name, path=path)
        assert theme.name == theme_name
        assert theme.elements['upvote'] == (-1, -1, curses.A_NORMAL)

        # Relative to the directory
        theme = Theme.from_name(theme_name, path=path)
        assert theme.name == theme_name
        assert theme.elements['upvote'] == (-1, -1, curses.A_NORMAL)

        # Invalid theme name
        with pytest.raises(ConfigError, path=path):
            theme.from_name('invalid_theme_name')


def test_theme_initialize_attributes(stdscr):

    theme = Theme()

    # Can't access elements before initializing curses
    with pytest.raises(RuntimeError):
        theme.get('upvote')

    theme.bind_curses()

    # Our pre-computed required color pairs should have been correct
    assert len(theme._color_pair_map) == theme.required_color_pairs

    for element in Theme.DEFAULT_THEME:
        assert isinstance(theme.get(element), int)


def test_theme_initialize_attributes_monochrome(stdscr):

    theme = Theme(monochrome=True)
    theme.bind_curses()

    # Avoid making these curses calls if colors aren't initialized
    curses.init_pair.assert_not_called()
    curses.color_pair.assert_not_called()


def test_theme_list_themes():

    with NamedTemporaryFile(mode='w+', suffix='.cfg') as fp:
        path, filename = os.path.split(fp.name)
        theme_name = filename[:-4]

        fp.write('[theme]\n')
        fp.flush()

        Theme.print_themes(path)
        themes = Theme.list_themes(path)
        assert themes['custom'][theme_name].name == theme_name
        assert themes['default']['monochrome'].name == 'monochrome'

        # This also checks that all of the default themes are valid
        assert not themes['invalid']


def test_theme_list_themes_invalid():

    with NamedTemporaryFile(mode='w+', suffix='.cfg') as fp:
        path, filename = os.path.split(fp.name)
        theme_name = filename[:-4]

        fp.write('[theme]\n')
        fp.write('upvote = invalid value\n')
        fp.flush()

        Theme.print_themes(path)
        themes = Theme.list_themes(path)
        assert theme_name in themes['invalid']
        assert not themes['custom']

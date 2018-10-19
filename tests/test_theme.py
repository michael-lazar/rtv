import os
import shutil
import curses
from collections import OrderedDict
from contextlib import contextmanager
from tempfile import mkdtemp, NamedTemporaryFile

import pytest

from rtv.theme import Theme
from rtv.config import DEFAULT_THEMES
from rtv.exceptions import ConfigError

try:
    from unittest import mock
except ImportError:
    import mock


INVALID_ELEMENTS = OrderedDict([
    ('too_few_items', 'Upvote = blue\n'),
    ('too_many_items', 'Upvote = blue blue bold underline\n'),
    ('invalid_fg', 'Upvote = invalid blue\n'),
    ('invalid_bg', 'Upvote = blue invalid\n'),
    ('invalid_attr', 'Upvote = blue blue bold+invalid\n'),
    ('invalid_hex', 'Upvote = #fffff blue\n'),
    ('invalid_hex2', 'Upvote = #gggggg blue\n'),
    ('out_of_range', 'Upvote = ansi_256 blue\n'),
    ('something_invalid', 'non_existing_key_without_value\n')
])


@contextmanager
def _ephemeral_directory():
    # All of the temporary files for the theme tests must
    # be initialized in separate directories, so the tests
    # can run in parallel without accidentally loading theme
    # files from each other
    dirname = None
    try:
        dirname = mkdtemp()
        yield dirname
    finally:
        if dirname:
            shutil.rmtree(dirname, ignore_errors=True)


def test_theme_invalid_source():

    with pytest.raises(ValueError):
        Theme(name='default', source=None)
    with pytest.raises(ValueError):
        Theme(name=None, source='installed')


def test_theme_default_construct():

    theme = Theme()
    assert theme.name == 'default'
    assert theme.source == 'built-in'
    assert theme.required_colors == 8
    assert theme.required_color_pairs == 6
    for fg, bg, attr in theme.elements.values():
        assert isinstance(fg, int)
        assert isinstance(bg, int)
        assert isinstance(attr, int)


def test_theme_monochrome_construct():

    theme = Theme(use_color=False)
    assert theme.name == 'monochrome'
    assert theme.source == 'built-in'
    assert theme.required_colors == 0
    assert theme.required_color_pairs == 0


def test_theme_256_construct():

    elements = {'CursorBar1': (None, 101, curses.A_UNDERLINE)}
    theme = Theme(elements=elements)
    assert theme.elements['CursorBar1'] == (-1, 101, curses.A_UNDERLINE)
    assert theme.required_colors == 256


def test_theme_element_selected_attributes():

    elements = {
        'Normal':   (1,    2,    curses.A_REVERSE),
        'Selected': (2,    3,    None),
        'TitleBar': (4,    None, curses.A_BOLD),
        'Link':     (5,    None, None)}

    theme = Theme(elements=elements)
    assert theme.elements['Normal'] == (1, 2, curses.A_REVERSE)

    # All of the normal elements fallback to the attributes of "Normal"
    assert theme.elements['Selected'] == (2, 3, curses.A_REVERSE)
    assert theme.elements['TitleBar'] == (4, 2, curses.A_BOLD)
    assert theme.elements['Link'] == (5, 2, curses.A_REVERSE)

    # The @Selected mode will overwrite any other attributes with
    # the ones defined in "Selected". Because "Selected" defines
    # a foreground and a background color, they will override the
    # ones that "Link" had defined.
    # assert theme.elements['@Link'] == (2, 3, curses.A_REVERSE)

    # I can't remember why the above rule was implemented, so I reverted it
    assert theme.elements['@Link'] == (5, 3, curses.A_REVERSE)

    assert '@Normal' not in theme.elements
    assert '@Selected' not in theme.elements
    assert '@TitleBar' not in theme.elements


def test_theme_default_cfg_matches_builtin():

    filename = os.path.join(DEFAULT_THEMES, 'default.cfg.example')
    default_theme = Theme.from_file(filename, 'built-in')

    # The default theme file should match the hardcoded values
    assert default_theme.elements == Theme().elements

    # Make sure that the elements passed into the constructor exactly match
    # up with the hardcoded elements
    class MockTheme(Theme):
        def __init__(self, name=None, source=None, elements=None):
            assert name == 'default.cfg'
            assert source == 'preset'
            assert elements == Theme.DEFAULT_ELEMENTS

    MockTheme.from_file(filename, 'preset')


args, ids = INVALID_ELEMENTS.values(), list(INVALID_ELEMENTS)
@pytest.mark.parametrize('line', args, ids=ids)
def test_theme_from_file_invalid(line):

    with _ephemeral_directory() as dirname:
        with NamedTemporaryFile(mode='w+', dir=dirname) as fp:
            fp.write('[theme]\n')
            fp.write(line)
            fp.flush()
            with pytest.raises(ConfigError):
                Theme.from_file(fp.name, 'installed')


def test_theme_from_file():

    with _ephemeral_directory() as dirname:
        with NamedTemporaryFile(mode='w+', dir=dirname) as fp:

            with pytest.raises(ConfigError):
                Theme.from_file(fp.name, 'installed')

            fp.write('[theme]\n')
            fp.write('Unknown = - -\n')
            fp.write('Upvote = - red\n')
            fp.write('Downvote = ansi_255 default bold\n')
            fp.write('NeutralVote = #000000 #ffffff bold+reverse\n')
            fp.flush()

            theme = Theme.from_file(fp.name, 'installed')
            assert theme.source == 'installed'
            assert 'Unknown' not in theme.elements
            assert theme.elements['Upvote'] == (
                -1, curses.COLOR_RED, curses.A_NORMAL)
            assert theme.elements['Downvote'] == (
                255, -1, curses.A_BOLD)
            assert theme.elements['NeutralVote'] == (
                16, 231, curses.A_BOLD | curses.A_REVERSE)


def test_theme_from_name():

    with _ephemeral_directory() as dirname:
        with NamedTemporaryFile(mode='w+', suffix='.cfg', dir=dirname) as fp:
            path, filename = os.path.split(fp.name)
            theme_name = filename[:-4]

            fp.write('[theme]\n')
            fp.write('Upvote = default default\n')
            fp.flush()

            # Full file path
            theme = Theme.from_name(fp.name, path=path)
            assert theme.name == theme_name
            assert theme.source == 'custom'
            assert theme.elements['Upvote'] == (-1, -1, curses.A_NORMAL)

            # Relative to the directory
            theme = Theme.from_name(theme_name, path=path)
            assert theme.name == theme_name
            assert theme.source == 'installed'
            assert theme.elements['Upvote'] == (-1, -1, curses.A_NORMAL)

            # Invalid theme name
            with pytest.raises(ConfigError):
                theme.from_name('invalid_theme_name', path=path)


def test_theme_initialize_attributes(stdscr):

    theme = Theme()
    with pytest.raises(RuntimeError):
        theme.get('Upvote')

    theme.bind_curses()
    assert len(theme._color_pair_map) == theme.required_color_pairs
    for element in Theme.DEFAULT_ELEMENTS:
        assert isinstance(theme.get(element), int)

    theme = Theme(use_color=False)
    theme.bind_curses()


def test_theme_initialize_attributes_monochrome(stdscr):

    theme = Theme(use_color=False)
    theme.bind_curses()
    theme.get('Upvote')

    # Avoid making these curses calls if colors aren't initialized
    assert not curses.init_pair.called
    assert not curses.color_pair.called


def test_theme_list_themes():

    with _ephemeral_directory() as dirname:
        with NamedTemporaryFile(mode='w+', suffix='.cfg', dir=dirname) as fp:
            path, filename = os.path.split(fp.name)
            theme_name = filename[:-4]

            fp.write('[theme]\n')
            fp.flush()

            Theme.print_themes(path)
            themes, errors = Theme.list_themes(path)
            assert not errors

            theme_strings = [t.display_string for t in themes]
            assert theme_name + ' (installed)' in theme_strings
            assert 'default (built-in)' in theme_strings
            assert 'monochrome (built-in)' in theme_strings
            assert 'molokai (preset)' in theme_strings


def test_theme_list_themes_invalid():

    with _ephemeral_directory() as dirname:
        with NamedTemporaryFile(mode='w+', suffix='.cfg', dir=dirname) as fp:
            path, filename = os.path.split(fp.name)
            theme_name = filename[:-4]

            fp.write('[theme]\n')
            fp.write('Upvote = invalid value\n')
            fp.flush()

            Theme.print_themes(path)
            themes, errors = Theme.list_themes(path)
            assert ('installed', theme_name) in errors


def test_theme_presets_define_all_elements():

    # The themes in the preset themes/ folder should have all of the valid
    # elements defined in their configuration.
    class MockTheme(Theme):

        def __init__(self, name=None, source=None, elements=None, use_color=True):
            if source == 'preset':
                assert set(elements.keys()) == set(Theme.DEFAULT_ELEMENTS.keys())
            super(MockTheme, self).__init__(name, source, elements, use_color)

    themes, errors = MockTheme.list_themes()
    assert sum([theme.source == 'preset' for theme in themes]) >= 4

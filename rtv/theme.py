# pylint: disable=bad-whitespace

import os
import codecs
import curses
import logging
from collections import OrderedDict
from contextlib import contextmanager

import six
from six.moves import configparser

from .config import THEMES, DEFAULT_THEMES
from .exceptions import ConfigError

_logger = logging.getLogger(__name__)


class Theme(object):

    ATTRIBUTE_CODES = {
        '-': None,
        '': None,
        'normal': curses.A_NORMAL,
        'bold': curses.A_BOLD,
        'reverse': curses.A_REVERSE,
        'underline': curses.A_UNDERLINE,
        'standout': curses.A_STANDOUT
    }

    COLOR_CODES = {
        '-': None,
        'default': -1,
        'black': curses.COLOR_BLACK,
        'red': curses.COLOR_RED,
        'green': curses.COLOR_GREEN,
        'yellow': curses.COLOR_YELLOW,
        'blue': curses.COLOR_BLUE,
        'magenta': curses.COLOR_MAGENTA,
        'cyan': curses.COLOR_CYAN,
        'light_gray': curses.COLOR_WHITE,
        'dark_gray': 8,
        'bright_red': 9,
        'bright_green': 10,
        'bright_yellow': 11,
        'bright_blue': 12,
        'bright_magenta': 13,
        'bright_cyan': 14,
        'white': 15,
    }

    for i in range(256):
        COLOR_CODES['ansi_{0}'.format(i)] = i

    # For compatibility with as many terminals as possible, the default theme
    # can only use the 8 basic colors with the default color as the background
    DEFAULT_THEME = {
        'modifiers': {
            'Normal':                (-1,                   -1,   curses.A_NORMAL),
            'Selected':              (-1,                   -1,   curses.A_NORMAL),
            'SelectedCursor':        (-1,                   -1,   curses.A_REVERSE),
        },
        'page': {
            'TitleBar':              (curses.COLOR_CYAN,    None, curses.A_BOLD | curses.A_REVERSE),
            'OrderBar':              (curses.COLOR_YELLOW,  None, curses.A_BOLD),
            'OrderBarHighlight':     (curses.COLOR_YELLOW,  None, curses.A_BOLD | curses.A_REVERSE),
            'HelpBar':               (curses.COLOR_CYAN,    None, curses.A_BOLD | curses.A_REVERSE),
            'Prompt':                (curses.COLOR_CYAN,    None, curses.A_BOLD | curses.A_REVERSE),
            'NoticeInfo':            (None,                 None, curses.A_BOLD),
            'NoticeLoading':         (None,                 None, curses.A_BOLD),
            'NoticeError':           (None,                 None, curses.A_BOLD),
            'NoticeSuccess':         (None,                 None, curses.A_BOLD),
        },
        # Fields that might be highlighted by the "SelectedCursor" element
        'cursor': {
            'CursorBlock':           (None,                 None, None),
            'CursorBar1':            (curses.COLOR_MAGENTA, None, None),
            'CursorBar2':            (curses.COLOR_CYAN,    None, None),
            'CursorBar3':            (curses.COLOR_GREEN,   None, None),
            'CursorBar4':            (curses.COLOR_YELLOW,  None, None),
        },
        # Fields that might be highlighted by the "Selected" element
        'normal': {
            'CommentAuthor':         (curses.COLOR_BLUE,    None, curses.A_BOLD),
            'CommentAuthorSelf':     (curses.COLOR_GREEN,   None, curses.A_BOLD),
            'CommentCount':          (None,                 None, None),
            'CommentText':           (None,                 None, None),
            'Created':               (None,                 None, None),
            'Downvote':              (curses.COLOR_RED,     None, curses.A_BOLD),
            'Gold':                  (curses.COLOR_YELLOW,  None, curses.A_BOLD),
            'HiddenCommentExpand':   (None,                 None, curses.A_BOLD),
            'HiddenCommentText':     (None,                 None, None),
            'MultiredditName':       (curses.COLOR_YELLOW,  None, curses.A_BOLD),
            'MultiredditText':       (None,                 None, None),
            'NeutralVote':           (None,                 None, curses.A_BOLD),
            'NSFW':                  (curses.COLOR_RED,     None, curses.A_BOLD | curses.A_REVERSE),
            'Saved':                 (curses.COLOR_GREEN,   None, None),
            'Hidden':                (curses.COLOR_YELLOW,  None, None),
            'Score':                 (None,                 None, None),
            'Separator':             (None,                 None, curses.A_BOLD),
            'Stickied':              (curses.COLOR_GREEN,   None, None),
            'SubscriptionName':      (curses.COLOR_YELLOW,  None, curses.A_BOLD),
            'SubscriptionText':      (None,                 None, None),
            'SubmissionAuthor':      (curses.COLOR_GREEN,   None, curses.A_BOLD),
            'SubmissionFlair':       (curses.COLOR_RED,     None, None),
            'SubmissionSubreddit':   (curses.COLOR_YELLOW,  None, None),
            'SubmissionText':        (None,                 None, None),
            'SubmissionTitle':       (None,                 None, curses.A_BOLD),
            'SubmissionTitleSeen':   (None,                 None, None),
            'Upvote':                (curses.COLOR_GREEN,   None, curses.A_BOLD),
            'Link':                  (curses.COLOR_BLUE,    None, curses.A_UNDERLINE),
            'LinkSeen':              (curses.COLOR_MAGENTA, None, curses.A_UNDERLINE),
            'UserFlair':             (curses.COLOR_YELLOW,  None, curses.A_BOLD)
        }
    }

    DEFAULT_ELEMENTS = {k: v for group in DEFAULT_THEME.values()
                        for k, v in group.items()}

    # The SubmissionPage uses this to determine which color bar to use
    CURSOR_BARS = ['CursorBar1', 'CursorBar2', 'CursorBar3', 'CursorBar4']

    def __init__(self, name=None, source=None, elements=None, use_color=True):
        """
        Params:
            name (str): A unique string that describes the theme
            source (str): A string that describes the source of the theme:
                built-in - Should only be used when Theme() is called directly
                preset - Themes packaged with rtv
                installed - Themes in ~/.config/rtv/themes/
                custom - When a filepath is explicitly provided, e.g.
                    ``rtv --theme=/path/to/theme_file.cfg``
            elements (dict): The theme's element map, should be in the same
                format as Theme.DEFAULT_THEME.
        """

        if source not in (None, 'built-in', 'preset', 'installed', 'custom'):
            raise ValueError('Invalid source')

        if name is None and source is None:
            name = 'default' if use_color else 'monochrome'
            source = 'built-in'
        elif name is None or source is None:
            raise ValueError('Must specify both `name` and `source`, or neither one')

        self.name = name
        self.source = source
        self.use_color = use_color

        self._color_pair_map = None
        self._attribute_map = None
        self._selected = None

        self.required_color_pairs = 0
        self.required_colors = 0

        if elements is None:
            elements = self.DEFAULT_ELEMENTS.copy()

        # Set any elements that weren't defined by the config to fallback to
        # the default color and attributes
        for key in self.DEFAULT_ELEMENTS.keys():
            if key not in elements:
                elements[key] = (None, None, None)

        self._set_fallback(elements, 'Normal', (-1, -1, curses.A_NORMAL))
        self._set_fallback(elements, 'Selected', 'Normal')
        self._set_fallback(elements, 'SelectedCursor', 'Normal')

        # Create the "Selected" versions of elements, which are prefixed with
        # the @ symbol. For example, "@CommentText" represents how comment
        # text is formatted when it is highlighted by the cursor.
        for key in self.DEFAULT_THEME['normal']:
            dest = '@{0}'.format(key)
            self._set_fallback(elements, key, 'Selected', dest)
        for key in self.DEFAULT_THEME['cursor']:
            dest = '@{0}'.format(key)
            self._set_fallback(elements, key, 'SelectedCursor', dest)

        # Fill in the ``None`` values for all of the elements with normal text
        for key in self.DEFAULT_THEME['normal']:
            self._set_fallback(elements, key, 'Normal')
        for key in self.DEFAULT_THEME['cursor']:
            self._set_fallback(elements, key, 'Normal')
        for key in self.DEFAULT_THEME['page']:
            self._set_fallback(elements, key, 'Normal')

        self.elements = elements

        if self.use_color:
            # Pre-calculate how many colors / color pairs the theme will need
            colors, color_pairs = set(), set()
            for fg, bg, _ in self.elements.values():
                colors.add(fg)
                colors.add(bg)
                color_pairs.add((fg, bg))

            # Don't count the default (-1, -1) as a color pair because it
            # doesn't need to be initialized by curses.init_pair().
            color_pairs.discard((-1, -1))
            self.required_color_pairs = len(color_pairs)

            # Determine how many colors the terminal needs to support in order
            # to be able to use the theme. This uses the common breakpoints
            # that 99% of terminals follow and doesn't take into account
            # 88 color themes.
            self.required_colors = None
            for marker in [0, 8, 16, 256]:
                if max(colors) < marker:
                    self.required_colors = marker
                    break

    @property
    def display_string(self):
        return '{0} ({1})'.format(self.name, self.source)

    def bind_curses(self):
        """
        Bind the theme's colors to curses's internal color pair map.

        This method must be called once (after curses has been initialized)
        before any element attributes can be accessed. Color codes and other
        special attributes will be mixed bitwise into a single value that
        can be passed into curses draw functions.
        """
        self._color_pair_map = {}
        self._attribute_map = {}

        for element, item in self.elements.items():
            fg, bg, attrs = item

            color_pair = (fg, bg)
            if self.use_color and color_pair != (-1, -1):
                # Curses limits the number of available color pairs, so we
                # need to reuse them if there are multiple elements with the
                # same foreground and background.
                if color_pair not in self._color_pair_map:
                    # Index 0 is reserved by curses for the default color
                    index = len(self._color_pair_map) + 1
                    curses.init_pair(index, color_pair[0], color_pair[1])
                    self._color_pair_map[color_pair] = curses.color_pair(index)
                attrs |= self._color_pair_map[color_pair]

            self._attribute_map[element] = attrs

    def get(self, element, selected=False):
        """
        Returns the curses attribute code for the given element.
        """
        if self._attribute_map is None:
            raise RuntimeError('Attempted to access theme attribute before '
                               'calling initialize_curses_theme()')

        if selected or self._selected:
            element = '@{0}'.format(element)

        return self._attribute_map[element]

    @contextmanager
    def turn_on_selected(self):
        """
        Sets the selected modifier inside of context block.

        For example:
            >>> with theme.turn_on_selected():
            >>>     attr = theme.get('CursorBlock')

        Is the same as:
            >>> attr = theme.get('CursorBlock', selected=True)

        Is also the same as:
            >>> attr = theme.get('@CursorBlock')

        """
        # This context manager should never be nested
        assert self._selected is None

        self._selected = True
        try:
            yield
        finally:
            self._selected = None

    @classmethod
    def list_themes(cls, path=THEMES):
        """
        Compile all of the themes configuration files in the search path.
        """
        themes, errors = [], OrderedDict()

        def load_themes(path, source):
            """
            Load all themes in the given path.
            """
            if os.path.isdir(path):
                for filename in sorted(os.listdir(path)):
                    if not filename.endswith('.cfg'):
                        continue

                    filepath = os.path.join(path, filename)
                    name = filename[:-4]
                    try:
                        # Make sure the theme is valid
                        theme = cls.from_file(filepath, source)
                    except Exception as e:
                        errors[(source, name)] = e
                    else:
                        themes.append(theme)

        themes.extend([Theme(use_color=True), Theme(use_color=False)])
        load_themes(DEFAULT_THEMES, 'preset')
        load_themes(path, 'installed')

        return themes, errors

    @classmethod
    def print_themes(cls, path=THEMES):
        """
        Prints a human-readable summary of the installed themes to stdout.

        This is intended to be used as a command-line utility, outside of the
        main curses display loop.
        """
        themes, errors = cls.list_themes(path=path + '/')

        print('\nInstalled ({0}):'.format(path))
        installed = [t for t in themes if t.source == 'installed']
        if installed:
            for theme in installed:
                line = '    {0:<20}[requires {1} colors]'
                print(line.format(theme.name, theme.required_colors))
        else:
            print('    (empty)')

        print('\nPresets:')
        preset = [t for t in themes if t.source == 'preset']
        for theme in preset:
            line = '    {0:<20}[requires {1} colors]'
            print(line.format(theme.name, theme.required_colors))

        print('\nBuilt-in:')
        built_in = [t for t in themes if t.source == 'built-in']
        for theme in built_in:
            line = '    {0:<20}[requires {1} colors]'
            print(line.format(theme.name, theme.required_colors))

        if errors:
            print('\nWARNING: Some files encountered errors:')
            for (source, name), error in errors.items():
                theme_info = '({0}) {1}'.format(source, name)
                # Align multi-line error messages with the right column
                err_message = six.text_type(error).replace('\n', '\n' + ' ' * 20)
                print('    {0:<20}{1}'.format(theme_info, err_message))

        print('')

    @classmethod
    def from_name(cls, name, path=THEMES):
        """
        Search for the given theme on the filesystem and attempt to load it.

        Directories will be checked in a pre-determined order. If the name is
        provided as an absolute file path, it will be loaded directly.
        """

        if os.path.isfile(name):
            return cls.from_file(name, 'custom')

        filename = os.path.join(path, '{0}.cfg'.format(name))
        if os.path.isfile(filename):
            return cls.from_file(filename, 'installed')

        filename = os.path.join(DEFAULT_THEMES, '{0}.cfg'.format(name))
        if os.path.isfile(filename):
            return cls.from_file(filename, 'preset')

        raise ConfigError('Could not find theme named "{0}"'.format(name))

    @classmethod
    def from_file(cls, filename, source):
        """
        Load a theme from the specified configuration file.

        Parameters:
            filename: The name of the filename to load.
            source: A description of where the theme was loaded from.
        """
        _logger.info('Loading theme %s', filename)

        try:
            config = configparser.ConfigParser()
            config.optionxform = six.text_type  # Preserve case
            with codecs.open(filename, encoding='utf-8') as fp:
                config.readfp(fp)
        except configparser.ParsingError as e:
            raise ConfigError(e.message)

        if not config.has_section('theme'):
            raise ConfigError(
                'Error loading {0}:\n'
                '    missing [theme] section'.format(filename))

        theme_name = os.path.basename(filename)
        theme_name, _ = os.path.splitext(theme_name)

        elements = {}
        for element, line in config.items('theme'):
            if element not in cls.DEFAULT_ELEMENTS:
                # Could happen if using a new config with an older version
                # of the software
                _logger.info('Skipping element %s', element)
                continue
            elements[element] = cls._parse_line(element, line, filename)

        return cls(name=theme_name, source=source, elements=elements)

    @classmethod
    def _parse_line(cls, element, line, filename=None):
        """
        Parse a single line from a theme file.

        Format:
            <element>: <foreground> <background> <attributes>
        """

        items = line.split()
        if len(items) == 2:
            fg, bg, attrs = items[0], items[1], ''
        elif len(items) == 3:
            fg, bg, attrs = items
        else:
            raise ConfigError(
                'Error loading {0}, invalid line:\n'
                '    {1} = {2}'.format(filename, element, line))

        if fg.startswith('#'):
            fg = cls.rgb_to_ansi(fg)
        if bg.startswith('#'):
            bg = cls.rgb_to_ansi(bg)

        if fg not in cls.COLOR_CODES:
            raise ConfigError(
                'Error loading {0}, invalid <foreground>:\n'
                '    {1} = {2}'.format(filename, element, line))
        fg_code = cls.COLOR_CODES[fg]

        if bg not in cls.COLOR_CODES:
            raise ConfigError(
                'Error loading {0}, invalid <background>:\n'
                '    {1} = {2}'.format(filename, element, line))
        bg_code = cls.COLOR_CODES[bg]

        attrs_code = curses.A_NORMAL
        for attr in attrs.split('+'):
            if attr not in cls.ATTRIBUTE_CODES:
                raise ConfigError(
                    'Error loading {0}, invalid <attributes>:\n'
                    '    {1} = {2}'.format(filename, element, line))
            attr_code = cls.ATTRIBUTE_CODES[attr]
            if attr_code is None:
                attrs_code = None
                break
            else:
                attrs_code |= attr_code

        return fg_code, bg_code, attrs_code

    @staticmethod
    def _set_fallback(elements, src_field, fallback, dest_field=None):
        """
        Helper function used to set the fallback attributes of an element when
        they are defined by the configuration as "None" or "-".
        """

        if dest_field is None:
            dest_field = src_field
        if isinstance(fallback, six.string_types):
            fallback = elements[fallback]

        attrs = elements[src_field]
        elements[dest_field] = (
            attrs[0] if attrs[0] is not None else fallback[0],
            attrs[1] if attrs[1] is not None else fallback[1],
            attrs[2] if attrs[2] is not None else fallback[2])

    @staticmethod
    def rgb_to_ansi(color):
        """
        Converts hex RGB to the 6x6x6 xterm color space

        Args:
            color (str): RGB color string in the format "#RRGGBB"

        Returns:
            str: ansi color string in the format "ansi_n", where n
                is between 16 and 230

        Reference:
            https://github.com/chadj2/bash-ui/blob/master/COLORS.md
        """

        if color[0] != '#' or len(color) != 7:
            return None

        try:
            r = round(int(color[1:3], 16) / 51.0)  # Normalize between 0-5
            g = round(int(color[3:5], 16) / 51.0)
            b = round(int(color[5:7], 16) / 51.0)
            n = int(36 * r + 6 * g + b + 16)
            return 'ansi_{0:d}'.format(n)
        except ValueError:
            return None


class ThemeList(object):
    """
    This is a small container around Theme.list_themes() that can be used
    to cycle through all of the available themes.
    """

    def __init__(self):
        self.themes = None
        self.errors = None

    def reload(self):
        """
        This acts as a lazy load, it won't read all of the theme files from
        disk until the first time somebody tries to access the theme list.
        """
        self.themes, self.errors = Theme.list_themes()

    def _step(self, theme, direction):
        """
        Traverse the list in the given direction and return the next theme
        """
        if not self.themes:
            self.reload()

        # Try to find the starting index
        key = (theme.source, theme.name)
        for i, val in enumerate(self.themes):
            if (val.source, val.name) == key:
                index = i
                break
        else:
            # If the theme was set from a custom source it might
            # not be a part of the list returned by list_themes().
            self.themes.insert(0, theme)
            index = 0

        index = (index + direction) % len(self.themes)
        new_theme = self.themes[index]
        return new_theme

    def next(self, theme):
        return self._step(theme, 1)

    def previous(self, theme):
        return self._step(theme, -1)

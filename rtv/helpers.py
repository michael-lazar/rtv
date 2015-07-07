import sys
import os
import curses
import webbrowser
import subprocess
from datetime import datetime
from tempfile import NamedTemporaryFile

# kitchen solves deficiencies in textwrap's handling of unicode characters
from kitchen.text.display import wrap, textual_width_chop
import six

from . import config
from .exceptions import ProgramError

__all__ = ['open_browser', 'clean', 'wrap_text', 'strip_textpad',
           'strip_subreddit_url', 'humanize_timestamp', 'open_editor']


def clean(string, n_cols=None):
    """
    Required reading!
        http://nedbatchelder.com/text/unipain.html

    Python 2 input string will be a unicode type (unicode code points). Curses
    will accept unicode if all of the points are in the ascii range. However, if
    any of the code points are not valid ascii curses will throw a
    UnicodeEncodeError: 'ascii' codec can't encode character, ordinal not in
    range(128). If we encode the unicode to a utf-8 byte string and pass that to
    curses, it will render correctly.

    Python 3 input string will be a string type (unicode code points). Curses
    will accept that in all cases. However, the n character count in addnstr
    will not be correct. If code points are passed to addnstr, curses will treat
    each code point as one character and will not account for wide characters.
    If utf-8 is passed in, addnstr will treat each 'byte' as a single character.
    """

    if n_cols is not None and n_cols <= 0:
        return ''

    if not config.unicode:
        if six.PY3 or isinstance(string, unicode):
            string = string.encode('ascii', 'replace')
        return string[:n_cols] if n_cols else string
    else:
        if n_cols:
            string = textual_width_chop(string, n_cols)
        if six.PY3 or isinstance(string, unicode):
            string = string.encode('utf-8')
        return string


def open_editor(data=''):
    """
    Open a temporary file using the system's default editor.

    The data string will be written to the file before opening. This function
    will block until the editor has closed. At that point the file will be
    read and and lines starting with '#' will be stripped.
    """

    with NamedTemporaryFile(prefix='rtv-', suffix='.txt', mode='wb') as fp:
        fp.write(clean(data))
        fp.flush()
        editor = os.getenv('RTV_EDITOR') or os.getenv('EDITOR') or 'nano'

        curses.endwin()
        try:
            subprocess.Popen([editor, fp.name]).wait()
        except OSError:
            raise ProgramError(editor)
        curses.doupdate()

        # Open a second file object to read. This appears to be necessary in
        # order to read the changes made by some editors (gedit). w+ mode does
        # not work!
        with open(fp.name) as fp2:
            text = ''.join(line for line in fp2 if not line.startswith('#'))
            text = text.rstrip()

    return text


def open_browser(url):
    """
    Open the given url using the default webbrowser. The preferred browser can
    specified with the $BROWSER environment variable. If not specified, python
    webbrowser will try to determine the default to use based on your system.

    For browsers requiring an X display, we call webbrowser.open_new_tab(url)
    and redirect stdout/stderr to devnull. This is a workaround to stop firefox
    from spewing warning messages to the console. See
    http://bugs.python.org/issue22277 for a better description of the problem.

    For console browsers (e.g. w3m), RTV will suspend and display the browser
    window within the same terminal. This mode is triggered either when
    1. $BROWSER is set to a known console browser, or
    2. $DISPLAY is undefined, indicating that the terminal is running headless

    There may be other cases where console browsers are opened (xdg-open?) but
    are not detected here.
    """

    console_browsers = ['www-browser', 'links', 'links2', 'elinks', 'lynx', 'w3m']

    display = bool(os.environ.get("DISPLAY"))

    # Use the convention defined here to parse $BROWSER
    # https://docs.python.org/2/library/webbrowser.html
    if "BROWSER" in os.environ:
        user_browser = os.environ["BROWSER"].split(os.pathsep)[0]
        if user_browser in console_browsers:
            display = False

    if webbrowser._tryorder and webbrowser._tryorder[0] in console_browsers:
        display = False

    if display:
        command = "import webbrowser; webbrowser.open_new_tab('%s')" % url
        args = [sys.executable, '-c', command]
        with open(os.devnull, 'ab+', 0) as null:
            subprocess.check_call(args, stdout=null, stderr=null)
    else:
        curses.endwin()
        webbrowser.open_new_tab(url)
        curses.doupdate()


def wrap_text(text, width):
    """
    Wrap text paragraphs to the given character width while preserving newlines.
    """
    out = []
    for paragraph in text.splitlines():
        # Wrap returns an empty list when paragraph is a newline. In order to
        # preserve newlines we substitute a list containing an empty string.
        lines = wrap(paragraph, width=width) or ['']
        out.extend(lines)
    return out


def strip_textpad(text):
    """
    Attempt to intelligently strip excess whitespace from the output of a
    curses textpad.
    """

    if text is None:
        return text

    # Trivial case where the textbox is only one line long.
    if '\n' not in text:
        return text.rstrip()

    # Allow one space at the end of the line. If there is more than one space,
    # assume that a newline operation was intended by the user
    stack, current_line = [], ''
    for line in text.split('\n'):
        if line.endswith('  '):
            stack.append(current_line + line.rstrip())
            current_line = ''
        else:
            current_line += line
    stack.append(current_line)

    # Prune empty lines at the bottom of the textbox.
    for item in stack[::-1]:
        if len(item) == 0:
            stack.pop()
        else:
            break

    out = '\n'.join(stack)
    return out


def strip_subreddit_url(permalink):
    """
    Strip a subreddit name from the subreddit's permalink.

    This is used to avoid submission.subreddit.url making a seperate API call.
    """

    subreddit = permalink.split('/')[4]
    return '/r/{}'.format(subreddit)


def humanize_timestamp(utc_timestamp, verbose=False):
    """
    Convert a utc timestamp into a human readable relative-time.
    """

    timedelta = datetime.utcnow() - datetime.utcfromtimestamp(utc_timestamp)

    seconds = int(timedelta.total_seconds())
    if seconds < 60:
        return 'moments ago' if verbose else '0min'
    minutes = seconds // 60
    if minutes < 60:
        return ('%d minutes ago' % minutes) if verbose else ('%dmin' % minutes)
    hours = minutes // 60
    if hours < 24:
        return ('%d hours ago' % hours) if verbose else ('%dhr' % hours)
    days = hours // 24
    if days < 30:
        return ('%d days ago' % days) if verbose else ('%dday' % days)
    months = days // 30.4
    if months < 12:
        return ('%d months ago' % months) if verbose else ('%dmonth' % months)
    years = months // 12
    return ('%d years ago' % years) if verbose else ('%dyr' % years)

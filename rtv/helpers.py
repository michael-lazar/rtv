import sys
import os
import textwrap
import subprocess
from datetime import datetime
from tempfile import NamedTemporaryFile

from . import config
from .exceptions import ProgramError

__all__ = ['open_browser', 'clean', 'wrap_text', 'strip_textpad',
           'strip_subreddit_url', 'humanize_timestamp', 'open_editor']

def open_editor(data=''):
    """
    Open a temporary file using the system's default editor.

    The data string will be written to the file before opening. This function
    will block until the editor has closed. At that point the file will be
    read and and lines starting with '#' will be stripped.
    """

    with NamedTemporaryFile(prefix='rtv-', suffix='.txt', mode='w') as fp:
        fp.write(data)
        fp.flush()
        editor = os.getenv('RTV_EDITOR') or os.getenv('EDITOR') or 'nano'

        try:
            subprocess.Popen([editor, fp.name]).wait()
        except OSError as e:
            raise ProgramError(editor)

        # Open a second file object to read. This appears to be necessary in
        # order to read the changes made by some editors (gedit). w+ mode does
        # not work!
        with open(fp.name) as fp2:
            text = ''.join(line for line in fp2 if not line.startswith('#'))
            text = text.rstrip()

    return text

def open_browser(url):
    """
    Call webbrowser.open_new_tab(url) and redirect stdout/stderr to devnull.

    This is a workaround to stop firefox from spewing warning messages to the
    console. See http://bugs.python.org/issue22277 for a better description
    of the problem.
    """
    command = "import webbrowser; webbrowser.open_new_tab('%s')" % url
    args = [sys.executable, '-c', command]
    with open(os.devnull, 'ab+', 0) as null:
        subprocess.check_call(args, stdout=null, stderr=null)

def clean(string):
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

    encoding = 'utf-8' if config.unicode else 'ascii'
    string = string.encode(encoding, 'replace')
    return string

def wrap_text(text, width):
    """
    Wrap text paragraphs to the given character width while preserving newlines.
    """
    out = []
    for paragraph in text.splitlines():
        # Wrap returns an empty list when paragraph is a newline. In order to
        # preserve newlines we substitute a list containing an empty string.
        lines = textwrap.wrap(paragraph, width=width) or ['']
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
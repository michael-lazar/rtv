"""Internal helper functions used by praw.decorators."""
import inspect
from requests.compat import urljoin
import six
import sys


def _get_captcha(reddit_session, captcha_id):
    """Prompt user for captcha solution and return a prepared result."""
    url = urljoin(reddit_session.config['captcha'],
                  captcha_id + '.png')
    sys.stdout.write('Captcha URL: {0}\nCaptcha: '.format(url))
    sys.stdout.flush()
    raw = sys.stdin.readline()
    if not raw:  # stdin has reached the end of file
        # Trigger exception raising next time through. The request is
        # cached so this will not require and extra request and delay.
        sys.stdin.close()
        return None
    return {'iden': captcha_id, 'captcha': raw.strip()}


def _is_mod_of_all(user, subreddit):
    mod_subs = user.get_cached_moderated_reddits()
    subs = six.text_type(subreddit).lower().split('+')
    return all(sub in mod_subs for sub in subs)


def _make_func_args(function):
    if six.PY3 and not hasattr(sys, 'pypy_version_info'):
        # CPython3 uses inspect.signature(), not inspect.getargspec()
        # see #551 and #541 for more info
        func_items = inspect.signature(function).parameters.items()
        func_args = [name for name, param in func_items
                     if param.kind == param.POSITIONAL_OR_KEYWORD]
    else:
        func_args = inspect.getargspec(function).args
    return func_args

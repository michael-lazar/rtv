# This file is part of PRAW.
#
# PRAW is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# PRAW is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# PRAW.  If not, see <http://www.gnu.org/licenses/>.

"""Internal helper functions.

The functions in this module are not to be relied upon by third-parties.

"""

from __future__ import print_function, unicode_literals
import os
import re
import six
import sys
from requests import Request, codes, exceptions
from requests.compat import urljoin
from praw.decorators import restrict_access
from praw.errors import (ClientException, HTTPException, Forbidden, NotFound,
                         InvalidSubreddit, OAuthException,
                         OAuthInsufficientScope, OAuthInvalidToken,
                         RedirectException)
from warnings import warn
try:
    from OpenSSL import __version__ as _opensslversion
    _opensslversionlist = [int(minor) if minor.isdigit() else minor
                           for minor in _opensslversion.split('.')]
except ImportError:
    _opensslversionlist = [0, 15]

MIN_PNG_SIZE = 67
MIN_JPEG_SIZE = 128
MAX_IMAGE_SIZE = 512000
JPEG_HEADER = b'\xff\xd8\xff'
PNG_HEADER = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'
RE_REDIRECT = re.compile('(rand(om|nsfw))|about/sticky')


def _get_redditor_listing(subpath=''):
    """Return function to generate Redditor listings."""
    def _listing(self, sort='new', time='all', *args, **kwargs):
        """Return a get_content generator for some RedditContentObject type.

        :param sort: Specify the sort order of the results if applicable
            (one of ``'hot'``, ``'new'``, ``'top'``, ``'controversial'``).
        :param time: Specify the time-period to return submissions if
            applicable (one of ``'hour'``, ``'day'``, ``'week'``,
            ``'month'``, ``'year'``, ``'all'``).

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        kwargs.setdefault('params', {})
        kwargs['params'].setdefault('sort', sort)
        kwargs['params'].setdefault('t', time)
        url = urljoin(self._url, subpath)  # pylint: disable=W0212
        return self.reddit_session.get_content(url, *args, **kwargs)
    return _listing


def _get_sorter(subpath='', **defaults):
    """Return function to generate specific subreddit Submission listings."""
    @restrict_access(scope='read')
    def _sorted(self, *args, **kwargs):
        """Return a get_content generator for some RedditContentObject type.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        if not kwargs.get('params'):
            kwargs['params'] = {}
        for key, value in six.iteritems(defaults):
            kwargs['params'].setdefault(key, value)
        url = urljoin(self._url, subpath)  # pylint: disable=W0212
        return self.reddit_session.get_content(url, *args, **kwargs)
    return _sorted


def _image_type(image):
    size = os.path.getsize(image.name)
    if size < MIN_PNG_SIZE:
        raise ClientException('png image is too small.')
    if size > MAX_IMAGE_SIZE:
        raise ClientException('`image` is too big. Max: {0} bytes'
                              .format(MAX_IMAGE_SIZE))
    first_bytes = image.read(MIN_PNG_SIZE)
    image.seek(0)
    if first_bytes.startswith(PNG_HEADER):
        return 'png'
    elif first_bytes.startswith(JPEG_HEADER):
        if size < MIN_JPEG_SIZE:
            raise ClientException('jpeg image is too small.')
        return 'jpg'
    raise ClientException('`image` must be either jpg or png.')


def _modify_relationship(relationship, unlink=False, is_sub=False):
    """Return a function for relationship modification.

    Used to support friending (user-to-user), as well as moderating,
    contributor creating, and banning (user-to-subreddit).

    """
    # The API uses friend and unfriend to manage all of these relationships.
    url_key = 'unfriend' if unlink else 'friend'

    if relationship == 'friend':
        access = {'scope': None, 'login': True}
    elif relationship == 'moderator':
        access = {'scope': 'modothers'}
    elif relationship in ['banned', 'contributor', 'muted']:
        access = {'scope': 'modcontributors'}
    elif relationship in ['wikibanned', 'wikicontributor']:
        access = {'scope': ['modcontributors', 'modwiki']}
    else:
        access = {'scope': None, 'mod': True}

    @restrict_access(**access)
    def do_relationship(thing, user, **kwargs):
        data = {'name': six.text_type(user),
                'type': relationship}
        data.update(kwargs)
        if is_sub:
            data['r'] = six.text_type(thing)
        else:
            data['container'] = thing.fullname

        session = thing.reddit_session
        if relationship == 'moderator':
            session.evict(session.config['moderators'].format(
                subreddit=six.text_type(thing)))
        url = session.config[url_key]
        return session.request_json(url, data=data)
    return do_relationship


def _prepare_request(reddit_session, url, params, data, auth, files,
                     method=None):
    """Return a requests Request object that can be "prepared"."""
    # Requests using OAuth for authorization must switch to using the oauth
    # domain.
    if getattr(reddit_session, '_use_oauth', False):
        bearer = 'bearer {0}'.format(reddit_session.access_token)
        headers = {'Authorization': bearer}
        config = reddit_session.config
        for prefix in (config.api_url, config.permalink_url):
            if url.startswith(prefix):
                if config.log_requests >= 1:
                    msg = 'substituting {0} for {1} in url\n'.format(
                        config.oauth_url, prefix)
                    sys.stderr.write(msg)
                url = config.oauth_url + url[len(prefix):]
                break
    else:
        headers = {}
    headers.update(reddit_session.http.headers)

    if method:
        pass
    elif data or files:
        method = 'POST'
    else:
        method = 'GET'

    # Log the request if logging is enabled
    if reddit_session.config.log_requests >= 1:
        sys.stderr.write('{0}: {1}\n'.format(method, url))
    if reddit_session.config.log_requests >= 2:
        if params:
            sys.stderr.write('params: {0}\n'.format(params))
        if data:
            sys.stderr.write('data: {0}\n'.format(data))
        if auth:
            sys.stderr.write('auth: {0}\n'.format(auth))
    # Prepare request
    request = Request(method=method, url=url, headers=headers, params=params,
                      auth=auth, cookies=reddit_session.http.cookies)
    if method == 'GET':
        return request
    # Most POST requests require adding `api_type` and `uh` to the data.
    if data is True:
        data = {}

    if isinstance(data, dict):
        if not auth:
            data.setdefault('api_type', 'json')
            if reddit_session.modhash:
                data.setdefault('uh', reddit_session.modhash)
    else:
        request.headers.setdefault('Content-Type', 'application/json')

    request.data = data
    request.files = files
    return request


def _raise_redirect_exceptions(response):
    """Return the new url or None if there are no redirects.

    Raise exceptions if appropriate.

    """
    if response.status_code not in [301, 302, 307]:
        return None
    new_url = urljoin(response.url, response.headers['location'])
    if 'reddits/search' in new_url:  # Handle non-existent subreddit
        subreddit = new_url.rsplit('=', 1)[1]
        raise InvalidSubreddit('`{0}` is not a valid subreddit'
                               .format(subreddit))
    elif not RE_REDIRECT.search(response.url):
        raise RedirectException(response.url, new_url)
    return new_url


def _raise_response_exceptions(response):
    """Raise specific errors on some status codes."""
    if not response.ok and 'www-authenticate' in response.headers:
        msg = response.headers['www-authenticate']
        if 'insufficient_scope' in msg:
            raise OAuthInsufficientScope('insufficient_scope', response.url)
        elif 'invalid_token' in msg:
            raise OAuthInvalidToken('invalid_token', response.url)
        else:
            raise OAuthException(msg, response.url)

    if response.status_code == codes.forbidden:  # pylint: disable=E1101
        raise Forbidden(_raw=response)
    elif response.status_code == codes.not_found:  # pylint: disable=E1101
        raise NotFound(_raw=response)
    else:
        try:
            response.raise_for_status()  # These should all be directly mapped
        except exceptions.HTTPError as exc:
            raise HTTPException(_raw=exc.response)


def _to_reddit_list(arg):
    """Return an argument converted to a reddit-formatted list.

    The returned format is a comma deliminated list. Each element is a string
    representation of an object. Either given as a string or as an object that
    is then converted to its string representation.
    """
    if (isinstance(arg, six.string_types) or not (
            hasattr(arg, "__getitem__") or hasattr(arg, "__iter__"))):
        return six.text_type(arg)
    else:
        return ','.join(six.text_type(a) for a in arg)


def _warn_pyopenssl():
    """Warn the user against faulty versions of pyOpenSSL."""
    if _opensslversionlist < [0, 15]:  # versions >= 0.15 are fine
        warn(RuntimeWarning(
            "pyOpenSSL {0} may be incompatible with praw if validating"
            "ssl certificates, which is on by default.\nSee https://"
            "github.com/praw/pull/625 for more information".format(
                _opensslversion)
        ))

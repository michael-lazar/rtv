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

"""
Python Reddit API Wrapper.

PRAW, an acronym for "Python Reddit API Wrapper", is a python package that
allows for simple access to reddit's API. PRAW aims to be as easy to use as
possible and is designed to follow all of reddit's API rules. You have to give
a useragent, everything else is handled by PRAW so you needn't worry about
violating them.

More information about PRAW can be found at https://github.com/praw-dev/praw
"""

from __future__ import print_function, unicode_literals

import json
import os
import platform
import re
import six
import sys
from . import decorators, errors
from .handlers import DefaultHandler
from .helpers import chunk_sequence, normalize_url
from .internal import (_image_type, _prepare_request,
                       _raise_redirect_exceptions,
                       _raise_response_exceptions,
                       _to_reddit_list, _warn_pyopenssl)
from .settings import CONFIG
from requests import Session
from requests.compat import urljoin
from requests.utils import to_native_string
from requests import Request
# pylint: disable=F0401
from six.moves import html_entities, http_cookiejar
from six.moves.urllib.parse import parse_qs, urlparse, urlunparse
# pylint: enable=F0401
from warnings import warn_explicit


__version__ = '3.6.1'


class Config(object):  # pylint: disable=R0903
    """A class containing the configuration for a reddit site."""

    API_PATHS = {'accept_mod_invite':   'api/accept_moderator_invite',
                 'access_token_url':    'api/v1/access_token/',
                 'approve':             'api/approve/',
                 'authorize':           'api/v1/authorize/',
                 'banned':              'r/{subreddit}/about/banned/',
                 'blocked':             'prefs/blocked/',
                 'by_id':               'by_id/',
                 'captcha':             'captcha/',
                 'clearflairtemplates': 'api/clearflairtemplates/',
                 'collapse_message':    'api/collapse_message/',
                 'comment':             'api/comment/',
                 'comment_replies':     'message/comments/',
                 'comments':            'comments/',
                 'compose':             'api/compose/',
                 'contest_mode':        'api/set_contest_mode/',
                 'contributors':        'r/{subreddit}/about/contributors/',
                 'controversial':       'controversial/',
                 'default_subreddits':  'subreddits/default/',
                 'del':                 'api/del/',
                 'deleteflair':         'api/deleteflair',
                 'delete_redditor':     'api/delete_user',
                 'delete_sr_header':    'r/{subreddit}/api/delete_sr_header',
                 'delete_sr_image':     'r/{subreddit}/api/delete_sr_img',
                 'distinguish':         'api/distinguish/',
                 'domain':              'domain/{domain}/',
                 'duplicates':          'duplicates/{submissionid}/',
                 'edit':                'api/editusertext/',
                 'edited':              'r/{subreddit}/about/edited/',
                 'flair':               'api/flair/',
                 'flairconfig':         'api/flairconfig/',
                 'flaircsv':            'api/flaircsv/',
                 'flairlist':           'r/{subreddit}/api/flairlist/',
                 'flairselector':       'api/flairselector/',
                 'flairtemplate':       'api/flairtemplate/',
                 'friend':              'api/friend/',
                 'friend_v1':           'api/v1/me/friends/{user}',
                 'friends':             'prefs/friends/',
                 'gild_thing':          'api/v1/gold/gild/{fullname}/',
                 'gild_user':           'api/v1/gold/give/{username}/',
                 'help':                'help/',
                 'hide':                'api/hide/',
                 'ignore_reports':      'api/ignore_reports/',
                 'inbox':               'message/inbox/',
                 'info':                'api/info/',
                 'leavecontributor':    'api/leavecontributor',
                 'leavemoderator':      'api/leavemoderator',
                 'lock':                'api/lock/',
                 'login':               'api/login/',
                 'me':                  'api/v1/me',
                 'mentions':            'message/mentions',
                 'message':             'message/messages/{messageid}/',
                 'messages':            'message/messages/',
                 'moderators':          'r/{subreddit}/about/moderators/',
                 'modlog':              'r/{subreddit}/about/log/',
                 'modqueue':            'r/{subreddit}/about/modqueue/',
                 'mod_mail':            'r/{subreddit}/message/moderator/',
                 'morechildren':        'api/morechildren/',
                 'my_con_subreddits':   'subreddits/mine/contributor/',
                 'my_mod_subreddits':   'subreddits/mine/moderator/',
                 'my_multis':           'api/multi/mine/',
                 'my_subreddits':       'subreddits/mine/subscriber/',
                 'new':                 'new/',
                 'new_subreddits':      'subreddits/new/',
                 'marknsfw':            'api/marknsfw/',
                 'multireddit':         'user/{user}/m/{multi}/',
                 'multireddit_add':     ('api/multi/user/{user}/m/{multi}/r/'
                                         '{subreddit}'),
                 'multireddit_about':   'api/multi/user/{user}/m/{multi}/',
                 'multireddit_copy':    'api/multi/copy/',
                 'multireddit_mine':    'me/m/{multi}/',
                 'multireddit_rename':  'api/multi/rename/',
                 'multireddit_user':    'api/multi/user/{user}/',
                 'mute_sender':         'api/mute_message_author/',
                 'muted':               'r/{subreddit}/about/muted/',
                 'popular_subreddits':  'subreddits/popular/',
                 'post_replies':        'message/selfreply/',
                 'read_message':        'api/read_message/',
                 'reddit_url':          '/',
                 'register':            'api/register/',
                 'remove':              'api/remove/',
                 'report':              'api/report/',
                 'reports':             'r/{subreddit}/about/reports/',
                 'rising':              'rising/',
                 'rules':               'r/{subreddit}/about/rules/',
                 'save':                'api/save/',
                 'saved':               'saved/',
                 'search':              'r/{subreddit}/search/',
                 'search_reddit_names': 'api/search_reddit_names/',
                 'select_flair':        'api/selectflair/',
                 'sent':                'message/sent/',
                 'sticky':              'r/{subreddit}/about/sticky/',
                 'sticky_submission':   'api/set_subreddit_sticky/',
                 'site_admin':          'api/site_admin/',
                 'spam':                'r/{subreddit}/about/spam/',
                 'stylesheet':          'r/{subreddit}/about/stylesheet/',
                 'submit':              'api/submit/',
                 'sub_comments_gilded': 'r/{subreddit}/comments/gilded/',
                 'sub_recommendations': 'api/recommend/sr/{subreddits}',
                 'subreddit':           'r/{subreddit}/',
                 'subreddit_about':     'r/{subreddit}/about/',
                 'subreddit_comments':  'r/{subreddit}/comments/',
                 'subreddit_css':       'api/subreddit_stylesheet/',
                 'subreddit_random':    'r/{subreddit}/random/',
                 'subreddit_settings':  'r/{subreddit}/about/edit/',
                 'subreddit_traffic':   'r/{subreddit}/about/traffic/',
                 'subscribe':           'api/subscribe/',
                 'suggested_sort':      'api/set_suggested_sort/',
                 'top':                 'top/',
                 'uncollapse_message':  'api/uncollapse_message/',
                 'unfriend':            'api/unfriend/',
                 'unhide':              'api/unhide/',
                 'unlock':              'api/unlock/',
                 'unmarknsfw':          'api/unmarknsfw/',
                 'unmoderated':         'r/{subreddit}/about/unmoderated/',
                 'unmute_sender':       'api/unmute_message_author/',
                 'unignore_reports':    'api/unignore_reports/',
                 'unread':              'message/unread/',
                 'unread_message':      'api/unread_message/',
                 'unsave':              'api/unsave/',
                 'upload_image':        'api/upload_sr_img',
                 'user':                'user/{user}/',
                 'user_about':          'user/{user}/about/',
                 'username_available':  'api/username_available/',
                 'vote':                'api/vote/',
                 'wiki_edit':           'api/wiki/edit/',
                 'wiki_page':           'r/{subreddit}/wiki/{page}',  # No /
                 'wiki_page_editor':    ('r/{subreddit}/api/wiki/alloweditor/'
                                         '{method}'),
                 'wiki_page_settings':  'r/{subreddit}/wiki/settings/{page}',
                 'wiki_pages':          'r/{subreddit}/wiki/pages/',
                 'wiki_banned':         'r/{subreddit}/about/wikibanned/',
                 'wiki_contributors':   'r/{subreddit}/about/wikicontributors/'
                 }
    WWW_PATHS = set(['authorize'])

    @staticmethod
    def ua_string(praw_info):
        """Return the user-agent string.

        The user-agent string contains PRAW version and platform version info.

        """
        if os.environ.get('SERVER_SOFTWARE') is not None:
            # Google App Engine information
            # https://developers.google.com/appengine/docs/python/
            info = os.environ.get('SERVER_SOFTWARE')
        else:
            # Standard platform information
            info = platform.platform(True).encode('ascii', 'ignore')

        return '{0} PRAW/{1} Python/{2} {3}'.format(
            praw_info, __version__, sys.version.split()[0], info)

    def __init__(self, site_name, **kwargs):
        """Initialize PRAW's configuration."""
        def config_boolean(item):
            return item and item.lower() in ('1', 'yes', 'true', 'on')

        obj = dict(CONFIG.items(site_name))
        # Overwrite configuration file settings with those given during
        # instantiation of the Reddit instance.
        for key, value in kwargs.items():
            obj[key] = value

        self.api_url = 'https://' + obj['api_domain']
        self.permalink_url = 'https://' + obj['permalink_domain']
        self.oauth_url = ('https://' if config_boolean(obj['oauth_https'])
                          else 'http://') + obj['oauth_domain']
        self.api_request_delay = float(obj['api_request_delay'])
        self.by_kind = {obj['comment_kind']:    objects.Comment,
                        obj['message_kind']:    objects.Message,
                        obj['redditor_kind']:   objects.Redditor,
                        obj['submission_kind']: objects.Submission,
                        obj['subreddit_kind']:  objects.Subreddit,
                        'LabeledMulti':         objects.Multireddit,
                        'modaction':            objects.ModAction,
                        'more':                 objects.MoreComments,
                        'wikipage':             objects.WikiPage,
                        'wikipagelisting':      objects.WikiPageListing,
                        'UserList':             objects.UserList}
        self.by_object = dict((value, key) for (key, value) in
                              six.iteritems(self.by_kind))
        self.by_object[objects.LoggedInRedditor] = obj['redditor_kind']
        self.cache_timeout = float(obj['cache_timeout'])
        self.check_for_updates = config_boolean(obj['check_for_updates'])
        self.domain = obj['permalink_domain']
        self.output_chars_limit = int(obj['output_chars_limit'])
        self.log_requests = int(obj['log_requests'])
        self.http_proxy = (obj.get('http_proxy') or os.getenv('http_proxy') or
                           None)
        self.https_proxy = (obj.get('https_proxy') or
                            os.getenv('https_proxy') or None)
        # We use `get(...) or None` because `get` may return an empty string

        self.validate_certs = config_boolean(obj.get('validate_certs'))

        self.client_id = obj.get('oauth_client_id') or None
        self.client_secret = obj.get('oauth_client_secret') or None
        self.redirect_uri = obj.get('oauth_redirect_uri') or None
        self.grant_type = obj.get('oauth_grant_type') or None
        self.refresh_token = obj.get('oauth_refresh_token') or None
        self.store_json_result = config_boolean(obj.get('store_json_result'))

        if 'short_domain' in obj and obj['short_domain']:
            self._short_domain = 'http://' + obj['short_domain']
        else:
            self._short_domain = None
        self.timeout = float(obj['timeout'])
        try:
            self.user = obj['user'] if obj['user'] else None
            self.pswd = obj['pswd']
        except KeyError:
            self.user = self.pswd = None

    def __getitem__(self, key):
        """Return the URL for key."""
        prefix = self.permalink_url if key in self.WWW_PATHS else self.api_url
        return urljoin(prefix, self.API_PATHS[key])

    @property
    def short_domain(self):
        """Return the short domain of the reddit server.

        Used to generate the shortlink. For reddit.com the short_domain is
        redd.it.

        """
        if self._short_domain:
            return self._short_domain
        else:
            raise errors.ClientException('No short domain specified.')


class BaseReddit(object):
    """A base class that allows access to reddit's API.

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    RETRY_CODES = [502, 503, 504]
    update_checked = False
    openssl_warned = False

    def __init__(self, user_agent, site_name=None, handler=None,
                 disable_update_check=False, **kwargs):
        """Initialize our connection with a reddit server.

        The user_agent is how your application identifies itself. Read the
        official API guidelines for user_agents
        https://github.com/reddit/reddit/wiki/API. Applications using default
        user_agents such as "Python/urllib" are drastically limited.

        site_name allows you to specify which reddit you want to connect to.
        The installation defaults are reddit.com, if you only need to connect
        to reddit.com then you can safely ignore this. If you want to connect
        to another reddit, set site_name to the name of that reddit. This must
        match with an entry in praw.ini. If site_name is None, then the site
        name will be looked for in the environment variable REDDIT_SITE. If it
        is not found there, the default site name reddit matching reddit.com
        will be used.

        disable_update_check allows you to prevent an update check from
        occurring in spite of the check_for_updates setting in praw.ini.

        All additional parameters specified via kwargs will be used to
        initialize the Config object. This can be used to specify configuration
        settings during instantiation of the Reddit instance. See
        https://praw.readthedocs.io/en/latest/pages/configuration_files.html
        for more details.

        """
        if not user_agent or not isinstance(user_agent, six.string_types):
            raise TypeError('user_agent must be a non-empty string.')
        if 'bot' in user_agent.lower():
            warn_explicit(
                'The keyword `bot` in your user_agent may be problematic.',
                UserWarning, '', 0)

        self.config = Config(site_name or os.getenv('REDDIT_SITE') or 'reddit',
                             **kwargs)
        self.handler = handler or DefaultHandler()
        self.http = Session()
        self.http.headers['User-Agent'] = self.config.ua_string(user_agent)
        self.http.validate_certs = self.config.validate_certs

        # This `Session` object is only used to store request information that
        # is used to make prepared requests. It _should_ never be used to make
        # a direct request, thus we raise an exception when it is used.

        def _req_error(*_, **__):
            raise errors.ClientException('Do not make direct requests.')
        self.http.request = _req_error

        if self.config.http_proxy or self.config.https_proxy:
            self.http.proxies = {}
            if self.config.http_proxy:
                self.http.proxies['http'] = self.config.http_proxy
            if self.config.https_proxy:
                self.http.proxies['https'] = self.config.https_proxy
        self.modhash = None

        # Check for updates if permitted and this is the first Reddit instance
        # if not disable_update_check and not BaseReddit.update_checked \
        #         and self.config.check_for_updates:
        #     update_check(__name__, __version__)
        #     BaseReddit.update_checked = True

        # Warn against a potentially incompatible version of pyOpenSSL
        if not BaseReddit.openssl_warned and self.config.validate_certs:
            _warn_pyopenssl()
            BaseReddit.openssl_warned = True

        # Initial values
        self._use_oauth = False

    def _request(self, url, params=None, data=None, files=None, auth=None,
                 timeout=None, raw_response=False, retry_on_error=True,
                 method=None):
        """Given a page url and a dict of params, open and return the page.

        :param url: the url to grab content from.
        :param params: a dictionary containing the GET data to put in the url
        :param data: a dictionary containing the extra data to submit
        :param files: a dictionary specifying the files to upload
        :param auth: Add the HTTP authentication headers (see requests)
        :param timeout: Specifies the maximum time that the actual HTTP request
            can take.
        :param raw_response: return the response object rather than the
            response body
        :param retry_on_error: if True retry the request, if it fails, for up
            to 3 attempts
        :returns: either the response body or the response object

        """
        def build_key_items(url, params, data, auth, files, method):
            request = _prepare_request(self, url, params, data, auth, files,
                                       method)

            # Prepare extra arguments
            key_items = []
            oauth = request.headers.get('Authorization', None)
            for key_value in (params, data, request.cookies, auth, oauth):
                if isinstance(key_value, dict):
                    key_items.append(tuple(key_value.items()))
                elif isinstance(key_value, http_cookiejar.CookieJar):
                    key_items.append(tuple(key_value.get_dict().items()))
                else:
                    key_items.append(key_value)
            kwargs = {'_rate_domain': self.config.domain,
                      '_rate_delay': int(self.config.api_request_delay),
                      '_cache_ignore': bool(files) or raw_response,
                      '_cache_timeout': int(self.config.cache_timeout)}

            return (request, key_items, kwargs)

        def decode(match):
            return six.unichr(html_entities.name2codepoint[match.group(1)])

        def handle_redirect():
            response = None
            url = request.url
            while url:  # Manually handle 302 redirects
                request.url = url
                kwargs['_cache_key'] = (normalize_url(request.url),
                                        tuple(key_items))
                response = self.handler.request(
                    request=request.prepare(),
                    proxies=self.http.proxies,
                    timeout=timeout,
                    verify=self.http.validate_certs, **kwargs)

                if self.config.log_requests >= 2:
                    msg = 'status: {0}\n'.format(response.status_code)
                    sys.stderr.write(msg)
                url = _raise_redirect_exceptions(response)
                assert url != request.url
            return response

        timeout = self.config.timeout if timeout is None else timeout
        request, key_items, kwargs = build_key_items(url, params, data,
                                                     auth, files, method)

        tempauth = self._use_oauth
        remaining_attempts = 3 if retry_on_error else 1
        attempt_oauth_refresh = bool(self.refresh_token)
        while True:
            try:
                self._use_oauth = self.is_oauth_session()
                response = handle_redirect()
                _raise_response_exceptions(response)
                self.http.cookies.update(response.cookies)
                if raw_response:
                    return response
                else:
                    return re.sub('&([^;]+);', decode, response.text)
            except errors.OAuthInvalidToken as error:
                if not attempt_oauth_refresh:
                    raise
                attempt_oauth_refresh = False
                self._use_oauth = False
                self.refresh_access_information()
                self._use_oauth = tempauth
                request, key_items, kwargs = build_key_items(url, params,
                                                             data, auth, files,
                                                             method)
            except errors.HTTPException as error:
                remaining_attempts -= 1
                # pylint: disable=W0212
                if error._raw.status_code not in self.RETRY_CODES or \
                        remaining_attempts == 0:
                    raise
            finally:
                self._use_oauth = tempauth

    def _json_reddit_objecter(self, json_data):
        """Return an appropriate RedditObject from json_data when possible."""
        try:
            object_class = self.config.by_kind[json_data['kind']]
        except KeyError:
            if 'json' in json_data:
                if len(json_data) != 1:
                    msg = 'Unknown object type: {0}'.format(json_data)
                    warn_explicit(msg, UserWarning, '', 0)
                return json_data['json']
        else:
            return object_class.from_api_response(self, json_data['data'])
        return json_data

    def evict(self, urls):
        """Evict url(s) from the cache.

        :param urls: An iterable containing normalized urls.
        :returns: The number of items removed from the cache.

        """
        if isinstance(urls, six.string_types):
            urls = (urls,)
        return self.handler.evict(urls)

    @decorators.oauth_generator
    def get_content(self, url, params=None, limit=0, place_holder=None,
                    root_field='data', thing_field='children',
                    after_field='after', object_filter=None, **kwargs):
        """A generator method to return reddit content from a URL.

        Starts at the initial url, and fetches content using the `after`
        JSON data until `limit` entries have been fetched, or the
        `place_holder` has been reached.

        :param url: the url to start fetching content from
        :param params: dictionary containing extra GET data to put in the url
        :param limit: the number of content entries to fetch. If limit <= 0,
            fetch the default for your account (25 for unauthenticated
            users). If limit is None, then fetch as many entries as possible
            (reddit returns at most 100 per request, however, PRAW will
            automatically make additional requests as necessary).
        :param place_holder: if not None, the method will fetch `limit`
            content, stopping if it finds content with `id` equal to
            `place_holder`. The place_holder item is the last item to be
            yielded from this generator. Note that the use of `place_holder` is
            not 100% reliable as the place holder item may no longer exist due
            to being removed or deleted.
        :param root_field: indicates the field in the json response that holds
            the data. Most objects use 'data', however some (flairlist) don't
            have the 'data' object. Use None for the root object.
        :param thing_field: indicates the field under the root_field which
            contains the list of things. Most objects use 'children'.
        :param after_field: indicates the field which holds the after item
            element
        :param object_filter: if set to an integer value, fetch content from
            the corresponding list index in the JSON response. For example
            the JSON response for submission duplicates is a list of objects,
            and the object we want to fetch from is at index 1. So we set
            object_filter=1 to filter out the other useless list elements.
        :type place_holder: a string corresponding to a reddit base36 id
            without prefix, e.g. 'asdfasdf'
        :returns: a list of reddit content, of type Subreddit, Comment,
            Submission or user flair.

        """
        _use_oauth = kwargs.get('_use_oauth', self.is_oauth_session())

        objects_found = 0
        params = params or {}
        fetch_all = fetch_once = False
        if limit is None:
            fetch_all = True
            params['limit'] = 1024  # Just use a big number
        elif limit > 0:
            params['limit'] = limit
        else:
            fetch_once = True

        if hasattr(self, '_url_update'):
            url = self._url_update(url)  # pylint: disable=E1101

        # While we still need to fetch more content to reach our limit, do so.
        while fetch_once or fetch_all or objects_found < limit:
            if _use_oauth:  # Set the necessary _use_oauth value
                assert self._use_oauth is False
                self._use_oauth = _use_oauth
            try:
                page_data = self.request_json(url, params=params)
                if object_filter:
                    page_data = page_data[object_filter]
            finally:  # Restore _use_oauth value
                if _use_oauth:
                    self._use_oauth = False
            fetch_once = False
            root = page_data.get(root_field, page_data)
            for thing in root[thing_field]:
                yield thing
                objects_found += 1
                # Terminate when we've reached the limit, or place holder
                if objects_found == limit or (place_holder and
                                              thing.id == place_holder):
                    return
            # Set/update the 'after' parameter for the next iteration
            if root.get(after_field):
                # We use `root.get` to also test if the value evaluates to True
                params['after'] = root[after_field]
            else:
                return

    @decorators.raise_api_exceptions
    def request(self, url, params=None, data=None, retry_on_error=True,
                method=None):
        """Make a HTTP request and return the response.

        :param url: the url to grab content from.
        :param params: a dictionary containing the GET data to put in the url
        :param data: a dictionary containing the extra data to submit
        :param retry_on_error: if True retry the request, if it fails, for up
            to 3 attempts
        :param method: The HTTP method to use in the request.
        :returns: The HTTP response.
        """
        return self._request(url, params, data, raw_response=True,
                             retry_on_error=retry_on_error, method=method)

    @decorators.raise_api_exceptions
    def request_json(self, url, params=None, data=None, as_objects=True,
                     retry_on_error=True, method=None):
        """Get the JSON processed from a page.

        :param url: the url to grab content from.
        :param params: a dictionary containing the GET data to put in the url
        :param data: a dictionary containing the extra data to submit
        :param as_objects: if True return reddit objects else raw json dict.
        :param retry_on_error: if True retry the request, if it fails, for up
            to 3 attempts
        :returns: JSON processed page

        """
        if not url.endswith('.json'):
            url += '.json'
        response = self._request(url, params, data, method=method,
                                 retry_on_error=retry_on_error)
        hook = self._json_reddit_objecter if as_objects else None
        # Request url just needs to be available for the objecter to use
        self._request_url = url  # pylint: disable=W0201

        if response == '':
            # Some of the v1 urls don't return anything, even when they're
            # successful.
            return response

        data = json.loads(response, object_hook=hook)
        delattr(self, '_request_url')
        # Update the modhash
        if isinstance(data, dict) and 'data' in data \
                and 'modhash' in data['data']:
            self.modhash = data['data']['modhash']
        return data


class OAuth2Reddit(BaseReddit):
    """Provides functionality for obtaining reddit OAuth2 access tokens.

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    def __init__(self, *args, **kwargs):
        """Initialize an OAuth2Reddit instance."""
        super(OAuth2Reddit, self).__init__(*args, **kwargs)
        self.client_id = self.config.client_id
        self.client_secret = self.config.client_secret
        self.redirect_uri = self.config.redirect_uri

    def _handle_oauth_request(self, data):
        auth = (self.client_id, self.client_secret)
        url = self.config['access_token_url']
        response = self._request(url, auth=auth, data=data, raw_response=True)
        if not response.ok:
            msg = 'Unexpected OAuthReturn: {0}'.format(response.status_code)
            raise errors.OAuthException(msg, url)
        retval = response.json()
        if 'error' in retval:
            error = retval['error']
            if error == 'invalid_grant':
                raise errors.OAuthInvalidGrant(error, url)
            raise errors.OAuthException(retval['error'], url)
        return retval

    @decorators.require_oauth
    def get_access_information(self, code):
        """Return the access information for an OAuth2 authorization grant.

        :param code: the code received in the request from the OAuth2 server
        :returns: A dictionary with the key/value pairs for ``access_token``,
            ``refresh_token`` and ``scope``. The ``refresh_token`` value will
            be None when the OAuth2 grant is not refreshable. The ``scope``
            value will be a set containing the scopes the tokens are valid for.

        """
        if self.config.grant_type == 'password':
            data = {'grant_type': 'password',
                    'username': self.config.user,
                    'password': self.config.pswd}
        else:
            data = {'code': code, 'grant_type': 'authorization_code',
                    'redirect_uri': self.redirect_uri}
        retval = self._handle_oauth_request(data)
        return {'access_token': retval['access_token'],
                'refresh_token': retval.get('refresh_token'),
                'scope': set(retval['scope'].split(' '))}

    @decorators.require_oauth
    def get_authorize_url(self, state, scope='identity', refreshable=False):
        """Return the URL to send the user to for OAuth2 authorization.

        :param state: a unique string of your choice that represents this
            individual client
        :param scope: the reddit scope to ask permissions for. Multiple scopes
            can be enabled by passing in a container of strings.
        :param refreshable: when True, a permanent "refreshable" token is
            issued

        """
        params = {'client_id': self.client_id, 'response_type': 'code',
                  'redirect_uri': self.redirect_uri, 'state': state,
                  'scope': _to_reddit_list(scope)}
        params['duration'] = 'permanent' if refreshable else 'temporary'
        request = Request('GET', self.config['authorize'], params=params)
        return request.prepare().url

    @property
    def has_oauth_app_info(self):
        """Return True when OAuth credentials are associated with the instance.

        The necessary credentials are: ``client_id``, ``client_secret`` and
        ``redirect_uri``.

        """
        return all((self.client_id is not None,
                    self.client_secret is not None,
                    self.redirect_uri is not None))

    @decorators.require_oauth
    def refresh_access_information(self, refresh_token):
        """Return updated access information for an OAuth2 authorization grant.

        :param refresh_token: the refresh token used to obtain the updated
            information
        :returns: A dictionary with the key/value pairs for access_token,
            refresh_token and scope. The refresh_token value will be done when
            the OAuth2 grant is not refreshable. The scope value will be a set
            containing the scopes the tokens are valid for.

        Password grants aren't refreshable, so use `get_access_information()`
        again, instead.
        """
        if self.config.grant_type == 'password':
            data = {'grant_type': 'password',
                    'username': self.config.user,
                    'password': self.config.pswd}
        else:
            data = {'grant_type': 'refresh_token',
                    'redirect_uri': self.redirect_uri,
                    'refresh_token': refresh_token}
        retval = self._handle_oauth_request(data)
        return {'access_token': retval['access_token'],
                'refresh_token': refresh_token,
                'scope': set(retval['scope'].split(' '))}

    def set_oauth_app_info(self, client_id, client_secret, redirect_uri):
        """Set the app information to use with OAuth2.

        This function need only be called if your praw.ini site configuration
        does not already contain the necessary information.

        Go to https://www.reddit.com/prefs/apps/ to discover the appropriate
        values for your application.

        :param client_id: the client_id of your application
        :param client_secret: the client_secret of your application
        :param redirect_uri: the redirect_uri of your application

        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri


class UnauthenticatedReddit(BaseReddit):
    """This mixin provides bindings for basic functions of reddit's API.

    None of these functions require authenticated access to reddit's API.

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    def __init__(self, *args, **kwargs):
        """Initialize an UnauthenticatedReddit instance."""
        super(UnauthenticatedReddit, self).__init__(*args, **kwargs)
        # initialize to 1 instead of 0, because 0 does not reliably make
        # new requests.
        self._unique_count = 1

    def create_redditor(self, user_name, password, email=''):
        """Register a new user.

        :returns: The json response from the server.

        """
        data = {'email': email,
                'passwd': password,
                'passwd2': password,
                'user': user_name}
        return self.request_json(self.config['register'], data=data)

    def default_subreddits(self, *args, **kwargs):
        """Return a get_content generator for the default subreddits.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['default_subreddits']
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='read')
    def get_comments(self, subreddit, gilded_only=False, *args, **kwargs):
        """Return a get_content generator for comments in the given subreddit.

        :param gilded_only: If True only return gilded comments.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        key = 'sub_comments_gilded' if gilded_only else 'subreddit_comments'
        url = self.config[key].format(subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='read')
    def get_controversial(self, *args, **kwargs):
        """Return a get_content generator for controversial submissions.

        Corresponds to submissions provided by
        ``https://www.reddit.com/controversial/`` for the session.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['controversial'], *args, **kwargs)

    @decorators.restrict_access(scope='read')
    def get_domain_listing(self, domain, sort='hot', period=None, *args,
                           **kwargs):
        """Return a get_content generator for submissions by domain.

        Corresponds to the submissions provided by
        ``https://www.reddit.com/domain/{domain}``.

        :param domain: The domain to generate a submission listing for.
        :param sort: When provided must be one of 'hot', 'new', 'rising',
            'controversial, or 'top'. Defaults to 'hot'.
        :param period: When sort is either 'controversial', or 'top' the period
            can be either None (for account default), 'all', 'year', 'month',
            'week', 'day', or 'hour'.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        # Verify arguments
        if sort not in ('controversial', 'hot', 'new', 'rising', 'top'):
            raise TypeError('Invalid sort parameter.')
        if period not in (None, 'all', 'day', 'hour', 'month', 'week', 'year'):
            raise TypeError('Invalid period parameter.')
        if sort not in ('controversial', 'top') and period:
            raise TypeError('Period cannot be set for that sort argument.')

        url = self.config['domain'].format(domain=domain)
        if sort != 'hot':
            url += sort
        if period:  # Set or overwrite params 't' parameter
            kwargs.setdefault('params', {})['t'] = period
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='modflair')
    def get_flair(self, subreddit, redditor, **params):
        """Return the flair for a user on the given subreddit.

        :param subreddit: Can be either a Subreddit object or the name of a
            subreddit.
        :param redditor: Can be either a Redditor object or the name of a
            redditor.
        :returns: None if the user doesn't exist, otherwise a dictionary
            containing the keys `flair_css_class`, `flair_text`, and `user`.

        """
        name = six.text_type(redditor)
        params.update(name=name)
        url = self.config['flairlist'].format(
            subreddit=six.text_type(subreddit))
        data = self.request_json(url, params=params)
        if not data['users'] or \
                data['users'][0]['user'].lower() != name.lower():
            return None
        return data['users'][0]

    @decorators.restrict_access(scope='read')
    def get_front_page(self, *args, **kwargs):
        """Return a get_content generator for the front page submissions.

        Corresponds to the submissions provided by ``https://www.reddit.com/``
        for the session.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['reddit_url'], *args, **kwargs)

    @decorators.restrict_access(scope='read', generator_called=True)
    def get_info(self, url=None, thing_id=None, *args, **kwargs):
        """Look up existing items by thing_id (fullname) or url.

        :param url: A url to lookup.
        :param thing_id: A single thing_id, or a list of thing_ids. A thing_id
            can be any one of Comment (``t1_``), Link (``t3_``), or Subreddit
            (``t5_``) to lookup by fullname.
        :returns: When a single ``thing_id`` is provided, return the
            corresponding thing object, or ``None`` if not found. When a list
            of ``thing_id``s or a ``url`` is provided return a list of thing
            objects (up to ``limit``). ``None`` is returned if all of the
            thing_ids or the URL is invalid.

        The additional parameters are passed into :meth:`.get_content` after
        the `params` parameter is exctracted and used to update the dictionary
        of url parameters this function sends. Note: the `url` parameter
        cannot be altered.

        Also, if using thing_id and the `limit` parameter passed to
        :meth:`.get_content` is used to slice the list of retreived things
        before returning it to the user, for when `limit > 100` and
        `(limit % 100) > 0`, to ensure a maximum of `limit` thigns are
        returned.

        """
        if bool(url) == bool(thing_id):
            raise TypeError('Only one of url or thing_id is required!')

        # In these cases, we will have a list of things to return.
        # Otherwise, it will just be one item.
        if isinstance(thing_id, six.string_types) and ',' in thing_id:
            thing_id = thing_id.split(',')
        return_list = bool(url) or not isinstance(thing_id, six.string_types)

        if url:
            param_groups = [{'url': url}]
        else:
            if isinstance(thing_id, six.string_types):
                thing_id = [thing_id]
            id_chunks = chunk_sequence(thing_id, 100)
            param_groups = [{'id': ','.join(id_chunk)} for
                            id_chunk in id_chunks]

        items = []
        update_with = kwargs.pop('params', {})
        for param_group in param_groups:
            param_group.update(update_with)
            kwargs['params'] = param_group
            chunk = self.get_content(self.config['info'], *args, **kwargs)
            items.extend(list(chunk))

        # if using ids, manually set the limit
        if kwargs.get('limit'):
            items = items[:kwargs['limit']]

        if return_list:
            return items if items else None
        elif items:
            return items[0]
        else:
            return None

    @decorators.restrict_access(scope='read')
    def get_moderators(self, subreddit, **kwargs):
        """Return the list of moderators for the given subreddit."""
        url = self.config['moderators'].format(
            subreddit=six.text_type(subreddit))
        return self.request_json(url, **kwargs)

    @decorators.restrict_access(scope='read')
    def get_new(self, *args, **kwargs):
        """Return a get_content generator for new submissions.

        Corresponds to the submissions provided by
        ``https://www.reddit.com/new/`` for the session.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['new'], *args, **kwargs)

    def get_new_subreddits(self, *args, **kwargs):
        """Return a get_content generator for the newest subreddits.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['new_subreddits']
        return self.get_content(url, *args, **kwargs)

    def get_popular_subreddits(self, *args, **kwargs):
        """Return a get_content generator for the most active subreddits.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['popular_subreddits']
        return self.get_content(url, *args, **kwargs)

    def get_random_subreddit(self, nsfw=False):
        """Return a random Subreddit object.

        :param nsfw: When true, return a random NSFW Subreddit object. Calling
            in this manner will set the 'over18' cookie for the duration of the
            PRAW session.

        """
        path = 'random'
        if nsfw:
            self.http.cookies.set('over18', '1')
            path = 'randnsfw'
        url = self.config['subreddit'].format(subreddit=path)
        response = self._request(url, params={'unique': self._unique_count},
                                 raw_response=True)
        self._unique_count += 1
        return self.get_subreddit(response.url.rsplit('/', 2)[-2])

    def get_random_submission(self, subreddit='all'):
        """Return a random Submission object.

        :param subreddit: Limit the submission to the specified
            subreddit(s). Default: all

        """
        url = self.config['subreddit_random'].format(
            subreddit=six.text_type(subreddit))
        try:
            item = self.request_json(url,
                                     params={'unique': self._unique_count})
            self._unique_count += 1  # Avoid network-level caching
            return objects.Submission.from_json(item)
        except errors.RedirectException as exc:
            self._unique_count += 1
            return self.get_submission(exc.response_url)
        raise errors.ClientException('Expected exception not raised.')

    def get_redditor(self, user_name, *args, **kwargs):
        """Return a Redditor instance for the user_name specified.

        The additional parameters are passed directly into the
        :class:`.Redditor` constructor.

        """
        return objects.Redditor(self, user_name, *args, **kwargs)

    @decorators.restrict_access(scope='read')
    def get_rising(self, *args, **kwargs):
        """Return a get_content generator for rising submissions.

        Corresponds to the submissions provided by
        ``https://www.reddit.com/rising/`` for the session.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['rising'], *args, **kwargs)

    @decorators.restrict_access(scope='read')
    def get_rules(self, subreddit, bottom=False):
        """Return the json dictionary containing rules for a subreddit.

        :param subreddit: The subreddit whose rules we will return.

        """
        url = self.config['rules'].format(subreddit=six.text_type(subreddit))
        return self.request_json(url)

    @decorators.restrict_access(scope='read')
    def get_sticky(self, subreddit, bottom=False):
        """Return a Submission object for the sticky of the subreddit.

        :param bottom: Get the top or bottom sticky. If the subreddit has only
            a single sticky, it is considered the top one.

        """
        url = self.config['sticky'].format(subreddit=six.text_type(subreddit))
        param = {'num': 2} if bottom else None
        return objects.Submission.from_json(self.request_json(url,
                                                              params=param))

    def get_submission(self, url=None, submission_id=None, comment_limit=0,
                       comment_sort=None, params=None):
        """Return a Submission object for the given url or submission_id.

        :param comment_limit: The desired number of comments to fetch. If <= 0
            fetch the default number for the session's user. If None, fetch the
            maximum possible.
        :param comment_sort: The sort order for retrieved comments. When None
            use the default for the session's user.
        :param params: Dictionary containing extra GET data to put in the url.

        """
        if bool(url) == bool(submission_id):
            raise TypeError('One (and only one) of id or url is required!')
        if submission_id:
            url = urljoin(self.config['comments'], submission_id)
        return objects.Submission.from_url(self, url,
                                           comment_limit=comment_limit,
                                           comment_sort=comment_sort,
                                           params=params)

    def get_submissions(self, fullnames, *args, **kwargs):
        """Generate Submission objects for each item provided in `fullnames`.

        A submission fullname looks like `t3_<base36_id>`. Submissions are
        yielded in the same order they appear in `fullnames`.

        Up to 100 items are batched at a time -- this happens transparently.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` and `limit` parameters cannot be
        altered.

        """
        fullnames = fullnames[:]
        while fullnames:
            cur = fullnames[:100]
            fullnames[:100] = []
            url = self.config['by_id'] + ','.join(cur)
            for item in self.get_content(url, limit=len(cur), *args, **kwargs):
                yield item

    def get_subreddit(self, subreddit_name, *args, **kwargs):
        """Return a Subreddit object for the subreddit_name specified.

        The additional parameters are passed directly into the
        :class:`.Subreddit` constructor.

        """
        sr_name_lower = subreddit_name.lower()
        if sr_name_lower == 'random':
            return self.get_random_subreddit()
        elif sr_name_lower == 'randnsfw':
            return self.get_random_subreddit(nsfw=True)
        return objects.Subreddit(self, subreddit_name, *args, **kwargs)

    def get_subreddit_recommendations(self, subreddits, omit=None):
        """Return a list of recommended subreddits as Subreddit objects.

        Subreddits with activity less than a certain threshold, will not have
        any recommendations due to lack of data.

        :param subreddits: A list of subreddits (either names or Subreddit
            objects) to base the recommendations on.
        :param omit: A list of subreddits (either names or Subreddit
            objects) that will be filtered out of the result.

        """
        params = {'omit': _to_reddit_list(omit or [])}
        url = self.config['sub_recommendations'].format(
            subreddits=_to_reddit_list(subreddits))
        result = self.request_json(url, params=params)
        return [objects.Subreddit(self, sub['sr_name']) for sub in result]

    @decorators.restrict_access(scope='read')
    def get_top(self, *args, **kwargs):
        """Return a get_content generator for top submissions.

        Corresponds to the submissions provided by
        ``https://www.reddit.com/top/`` for the session.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['top'], *args, **kwargs)

    # There exists a `modtraffic` scope, but it is unused.
    @decorators.restrict_access(scope='modconfig')
    def get_traffic(self, subreddit):
        """Return the json dictionary containing traffic stats for a subreddit.

        :param subreddit: The subreddit whose /about/traffic page we will
            collect.

        """
        url = self.config['subreddit_traffic'].format(
            subreddit=six.text_type(subreddit))
        return self.request_json(url)

    @decorators.restrict_access(scope='wikiread', login=False)
    def get_wiki_page(self, subreddit, page):
        """Return a WikiPage object for the subreddit and page provided."""
        return objects.WikiPage(self, six.text_type(subreddit), page.lower())

    @decorators.restrict_access(scope='wikiread', login=False)
    def get_wiki_pages(self, subreddit):
        """Return a list of WikiPage objects for the subreddit."""
        url = self.config['wiki_pages'].format(
            subreddit=six.text_type(subreddit))
        return self.request_json(url)

    def is_username_available(self, username):
        """Return True if username is valid and available, otherwise False."""
        params = {'user': username}
        try:
            result = self.request_json(self.config['username_available'],
                                       params=params)
        except errors.BadUsername:
            return False
        return result

    def search(self, query, subreddit=None, sort=None, syntax=None,
               period=None, *args, **kwargs):
        """Return a generator for submissions that match the search query.

        :param query: The query string to search for. If query is a URL only
            submissions which link to that URL will be returned.
        :param subreddit: Limit search results to the subreddit if provided.
        :param sort: The sort order of the results.
        :param syntax: The syntax of the search query.
        :param period: The time period of the results.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        See https://www.reddit.com/wiki/search for more information on how to
        build a search query.

        """
        params = {'q': query}
        if 'params' in kwargs:
            params.update(kwargs['params'])
            kwargs.pop('params')
        if sort:
            params['sort'] = sort
        if syntax:
            params['syntax'] = syntax
        if period:
            params['t'] = period
        if subreddit:
            params['restrict_sr'] = 'on'
            subreddit = six.text_type(subreddit)
        else:
            subreddit = 'all'
        url = self.config['search'].format(subreddit=subreddit)

        depth = 2
        while depth > 0:
            depth -= 1
            try:
                for item in self.get_content(url, params=params, *args,
                                             **kwargs):
                    yield item
                break
            except errors.RedirectException as exc:
                parsed = urlparse(exc.response_url)
                params = dict((k, ",".join(v)) for k, v in
                              parse_qs(parsed.query).items())
                url = urlunparse(parsed[:3] + ("", "", ""))
                # Handle redirects from URL searches
                if 'already_submitted' in params:
                    yield self.get_submission(url)
                    break

    def search_reddit_names(self, query):
        """Return subreddits whose display name contains the query."""
        data = {'query': query}
        results = self.request_json(self.config['search_reddit_names'],
                                    data=data)
        return [self.get_subreddit(name) for name in results['names']]


class AuthenticatedReddit(OAuth2Reddit, UnauthenticatedReddit):
    """This class adds the methods necessary for authenticating with reddit.

    Authentication can either be login based
    (through :meth:`~praw.__init__.AuthenticatedReddit.login`), or OAuth2 based
    (via :meth:`~praw.__init__.AuthenticatedReddit.set_access_credentials`).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    def __init__(self, *args, **kwargs):
        """Initialize an AuthenticatedReddit instance."""
        super(AuthenticatedReddit, self).__init__(*args, **kwargs)
        # Add variable to distinguish between authentication type
        #  * None means unauthenticated
        #  * True mean login authenticated
        #  * set(...) means OAuth authenticated with the scopes in the set
        self._authentication = None
        self.access_token = None
        self.refresh_token = self.config.refresh_token or None
        self.user = None

    def __str__(self):
        """Return a string representation of the AuthenticatedReddit."""
        if isinstance(self._authentication, set):
            return 'OAuth2 reddit session (scopes: {0})'.format(
                ', '.join(self._authentication))
        elif self._authentication:
            return 'LoggedIn reddit session (user: {0})'.format(self.user)
        else:
            return 'Unauthenticated reddit session'

    def _url_update(self, url):
        # When getting posts from a multireddit owned by the authenticated
        # Redditor, we are redirected to me/m/multi/. Handle that now
        # instead of catching later.
        if re.search('user/.*/m/.*', url):
            redditor = url.split('/')[-4]
            if self.user and self.user.name.lower() == redditor.lower():
                url = url.replace("user/"+redditor, 'me')
        return url

    @decorators.restrict_access(scope='modself', mod=False)
    def accept_moderator_invite(self, subreddit):
        """Accept a moderator invite to the given subreddit.

        Callable upon an instance of Subreddit with no arguments.

        :returns: The json response from the server.

        """
        data = {'r': six.text_type(subreddit)}
        # Clear moderated subreddits and cache
        self.user._mod_subs = None  # pylint: disable=W0212
        self.evict(self.config['my_mod_subreddits'])
        return self.request_json(self.config['accept_mod_invite'], data=data)

    def clear_authentication(self):
        """Clear any existing authentication on the reddit object.

        This function is implicitly called on `login` and
        `set_access_credentials`.

        """
        self._authentication = None
        self.access_token = None
        self.refresh_token = None
        self.http.cookies.clear()
        self.user = None

    def delete(self, password, message=""):
        """Delete the currently authenticated redditor.

        WARNING!

        This action is IRREVERSIBLE. Use only if you're okay with NEVER
        accessing this reddit account again.

        :param password: password for currently authenticated account
        :param message: optional 'reason for deletion' message.
        :returns: json response from the server.

        """
        data = {'user': self.user.name,
                'passwd': password,
                'delete_message': message,
                'confirm': True}
        return self.request_json(self.config['delete_redditor'], data=data)

    @decorators.restrict_access(scope='wikiedit')
    def edit_wiki_page(self, subreddit, page, content, reason=''):
        """Create or edit a wiki page with title `page` for `subreddit`.

        :returns: The json response from the server.

        """
        data = {'content': content,
                'page': page,
                'r': six.text_type(subreddit),
                'reason': reason}
        evict = self.config['wiki_page'].format(
            subreddit=six.text_type(subreddit), page=page.lower())
        self.evict(evict)
        return self.request_json(self.config['wiki_edit'], data=data)

    def get_access_information(self, code,  # pylint: disable=W0221
                               update_session=True):
        """Return the access information for an OAuth2 authorization grant.

        :param code: the code received in the request from the OAuth2 server
        :param update_session: Update the current session with the retrieved
            token(s).
        :returns: A dictionary with the key/value pairs for access_token,
            refresh_token and scope. The refresh_token value will be done when
            the OAuth2 grant is not refreshable.

        """
        retval = super(AuthenticatedReddit, self).get_access_information(code)
        if update_session:
            self.set_access_credentials(**retval)
        return retval

    @decorators.restrict_access(scope='flair')
    def get_flair_choices(self, subreddit, link=None):
        """Return available flair choices and current flair.

        :param link: If link is given, return the flair options for this
            submission. Not normally given directly, but instead set by calling
            the flair_choices method for Submission objects.
            Use the default for the session's user.

        :returns: A dictionary with 2 keys. 'current' containing current flair
            settings for the authenticated user and 'choices' containing a list
            of possible flair choices.

        """
        data = {'r':  six.text_type(subreddit), 'link': link}
        return self.request_json(self.config['flairselector'], data=data)

    @decorators.restrict_access(scope='read', login=True)
    def get_friends(self, **params):
        """Return a UserList of Redditors with whom the user is friends."""
        url = self.config['friends']
        return self.request_json(url, params=params)[0]

    @decorators.restrict_access(scope='identity', oauth_only=True)
    def get_me(self):
        """Return a LoggedInRedditor object.

        Note: This function is only intended to be used with an 'identity'
        providing OAuth2 grant.
        """
        response = self.request_json(self.config['me'])
        user = objects.Redditor(self, response['name'], response)
        user.__class__ = objects.LoggedInRedditor
        return user

    def has_scope(self, scope):
        """Return True if OAuth2 authorized for the passed in scope(s)."""
        if not self.is_oauth_session():
            return False
        if '*' in self._authentication:
            return True
        if isinstance(scope, six.string_types):
            scope = [scope]
        return all(s in self._authentication for s in scope)

    def is_logged_in(self):
        """Return True when the session is authenticated via username/password.

        Username and passwords are provided via
        :meth:`~praw.__init__.AuthenticatedReddit.login`.

        """
        return self._authentication is True

    def is_oauth_session(self):
        """Return True when the current session is an OAuth2 session."""
        return isinstance(self._authentication, set)

    @decorators.deprecated('reddit intends to disable password-based '
                           'authentication of API clients sometime in the '
                           'near future. As a result this method will be '
                           'removed in a future major version of PRAW.\n\n'
                           'For more information please see:\n\n'
                           '* Original reddit deprecation notice: '
                           'https://www.reddit.com/comments/2ujhkr/\n\n'
                           '* Updated delayed deprecation notice: '
                           'https://www.reddit.com/comments/37e2mv/\n\n'
                           'Pass ``disable_warning=True`` to ``login`` to '
                           'disable this warning.')
    def login(self, username=None, password=None, **kwargs):
        """Login to a reddit site.

        **DEPRECATED**. Will be removed in a future version of PRAW.

        https://www.reddit.com/comments/2ujhkr/
        https://www.reddit.com/comments/37e2mv/

        Look for username first in parameter, then praw.ini and finally if both
        were empty get it from stdin. Look for password in parameter, then
        praw.ini (but only if username matches that in praw.ini) and finally
        if they both are empty get it with getpass. Add the variables ``user``
        (username) and ``pswd`` (password) to your praw.ini file to allow for
        auto-login.

        A successful login will overwrite any existing authentication.

        """
        if password and not username:
            raise Exception('Username must be provided when password is.')
        user = username or self.config.user
        if not user:
            sys.stdout.write('Username: ')
            sys.stdout.flush()
            user = sys.stdin.readline().strip()
            pswd = None
        else:
            pswd = password or self.config.pswd
        if not pswd:
            import getpass
            pswd = getpass.getpass('Password for {0}: '.format(user)
                                   .encode('ascii', 'ignore'))

        data = {'passwd': pswd,
                'user': user}
        self.clear_authentication()
        self.request_json(self.config['login'], data=data)
        # Update authentication settings
        self._authentication = True
        self.user = self.get_redditor(user)
        self.user.__class__ = objects.LoggedInRedditor

    def refresh_access_information(self,  # pylint: disable=W0221
                                   refresh_token=None,
                                   update_session=True):
        """Return updated access information for an OAuth2 authorization grant.

        :param refresh_token: The refresh token used to obtain the updated
            information. When not provided, use the stored refresh_token.
        :param update_session: Update the session with the returned data.
        :returns: A dictionary with the key/value pairs for ``access_token``,
            ``refresh_token`` and ``scope``. The ``refresh_token`` value will
            be None when the OAuth2 grant is not refreshable. The ``scope``
            value will be a set containing the scopes the tokens are valid for.

        """
        response = super(AuthenticatedReddit, self).refresh_access_information(
            refresh_token=refresh_token or self.refresh_token)
        if update_session:
            self.set_access_credentials(**response)
        return response

    @decorators.restrict_access(scope='flair')
    def select_flair(self, item, flair_template_id='', flair_text=''):
        """Select user flair or link flair on subreddits.

        This can only be used for assigning your own name flair or link flair
        on your own submissions. For assigning other's flairs using moderator
        access, see :meth:`~praw.__init__.ModFlairMixin.set_flair`.

        :param item: A string, Subreddit object (for user flair), or
            Submission object (for link flair). If ``item`` is a string it
            will be treated as the name of a Subreddit.
        :param flair_template_id: The id for the desired flair template. Use
            the :meth:`~praw.objects.Subreddit.get_flair_choices` and
            :meth:`~praw.objects.Submission.get_flair_choices` methods to find
            the ids for the available user and link flair choices.
        :param flair_text: A string containing the custom flair text.
            Used on subreddits that allow it.

        :returns: The json response from the server.

        """
        data = {'flair_template_id': flair_template_id or '',
                'text':              flair_text or ''}
        if isinstance(item, objects.Submission):
            # Link flair
            data['link'] = item.fullname
            evict = item.permalink
        else:
            # User flair
            data['name'] = self.user.name
            data['r'] = six.text_type(item)
            evict = self.config['flairlist'].format(
                subreddit=six.text_type(item))
        response = self.request_json(self.config['select_flair'], data=data)
        self.evict(evict)
        return response

    @decorators.require_oauth
    def set_access_credentials(self, scope, access_token, refresh_token=None,
                               update_user=True):
        """Set the credentials used for OAuth2 authentication.

        Calling this function will overwrite any currently existing access
        credentials.

        :param scope: A set of reddit scopes the tokens provide access to
        :param access_token: the access token of the authentication
        :param refresh_token: the refresh token of the authentication
        :param update_user: Whether or not to set the user attribute for
            identity scopes

        """
        if isinstance(scope, (list, tuple)):
            scope = set(scope)
        elif isinstance(scope, six.string_types):
            scope = set(scope.split())
        if not isinstance(scope, set):
            raise TypeError('`scope` parameter must be a set')
        self.clear_authentication()
        # Update authentication settings
        self._authentication = scope
        self.access_token = access_token
        self.refresh_token = refresh_token
        # Update the user object
        if update_user and ('identity' in scope or '*' in scope):
            self.user = self.get_me()


class ModConfigMixin(AuthenticatedReddit):
    """Adds methods requiring the 'modconfig' scope (or mod access).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='modconfig', mod=False)
    @decorators.require_captcha
    def create_subreddit(self, name, title, description='', language='en',
                         subreddit_type='public', content_options='any',
                         over_18=False, default_set=True, show_media=False,
                         domain='', wikimode='disabled', captcha=None,
                         **kwargs):
        """Create a new subreddit.

        :returns: The json response from the server.

        This function may result in a captcha challenge. PRAW will
        automatically prompt you for a response. See :ref:`handling-captchas`
        if you want to manually handle captchas.

        """
        data = {'name': name,
                'title': title,
                'description': description,
                'lang': language,
                'type': subreddit_type,
                'link_type': content_options,
                'over_18': 'on' if over_18 else 'off',
                'allow_top': 'on' if default_set else 'off',
                'show_media': 'on' if show_media else 'off',
                'wikimode': wikimode,
                'domain': domain}
        if captcha:
            data.update(captcha)
        return self.request_json(self.config['site_admin'], data=data)

    @decorators.restrict_access(scope='modconfig')
    def delete_image(self, subreddit, name=None, header=False):
        """Delete an image from the subreddit.

        :param name: The name of the image if removing a CSS image.
        :param header: When true, delete the subreddit header.
        :returns: The json response from the server.

        """
        subreddit = six.text_type(subreddit)
        if name and header:
            raise TypeError('Both name and header cannot be set.')
        elif name:
            data = {'img_name': name}
            url = self.config['delete_sr_image']
            self.evict(self.config['stylesheet'].format(subreddit=subreddit))
        else:
            data = True
            url = self.config['delete_sr_header']
        url = url.format(subreddit=subreddit)
        return self.request_json(url, data=data)

    @decorators.restrict_access(scope='modconfig')
    def get_settings(self, subreddit, **params):
        """Return the settings for the given subreddit."""
        url = self.config['subreddit_settings'].format(
            subreddit=six.text_type(subreddit))
        return self.request_json(url, params=params)['data']

    @decorators.restrict_access(scope='modconfig')
    def set_settings(self, subreddit, title, public_description='',
                     description='', language='en', subreddit_type='public',
                     content_options='any', over_18=False, default_set=True,
                     show_media=False, domain='', domain_css=False,
                     domain_sidebar=False, header_hover_text='',
                     wikimode='disabled', wiki_edit_age=30,
                     wiki_edit_karma=100,
                     submit_link_label='', submit_text_label='',
                     exclude_banned_modqueue=False, comment_score_hide_mins=0,
                     public_traffic=False, collapse_deleted_comments=False,
                     spam_comments='low', spam_links='high',
                     spam_selfposts='high', submit_text='',
                     hide_ads=False, suggested_comment_sort='',
                     key_color='',
                     **kwargs):
        """Set the settings for the given subreddit.

        :param subreddit: Must be a subreddit object.
        :returns: The json response from the server.

        """
        data = {'sr': subreddit.fullname,
                'allow_top': default_set,
                'comment_score_hide_mins': comment_score_hide_mins,
                'collapse_deleted_comments': collapse_deleted_comments,
                'description': description,
                'domain': domain or '',
                'domain_css': domain_css,
                'domain_sidebar': domain_sidebar,
                'exclude_banned_modqueue': exclude_banned_modqueue,
                'header-title': header_hover_text or '',
                'hide_ads': hide_ads,
                'key_color': key_color,
                'lang': language,
                'link_type': content_options,
                'over_18': over_18,
                'public_description': public_description,
                'public_traffic': public_traffic,
                'show_media': show_media,
                'submit_link_label': submit_link_label or '',
                'submit_text': submit_text,
                'submit_text_label': submit_text_label or '',
                'suggested_comment_sort': suggested_comment_sort or '',
                'spam_comments': spam_comments,
                'spam_links': spam_links,
                'spam_selfposts': spam_selfposts,
                'title': title,
                'type': subreddit_type,
                'wiki_edit_age': six.text_type(wiki_edit_age),
                'wiki_edit_karma': six.text_type(wiki_edit_karma),
                'wikimode': wikimode}

        if kwargs:
            msg = 'Extra settings fields: {0}'.format(kwargs.keys())
            warn_explicit(msg, UserWarning, '', 0)
            data.update(kwargs)
        evict = self.config['subreddit_settings'].format(
            subreddit=six.text_type(subreddit))
        self.evict(evict)
        return self.request_json(self.config['site_admin'], data=data)

    @decorators.restrict_access(scope='modconfig')
    def set_stylesheet(self, subreddit, stylesheet):
        """Set stylesheet for the given subreddit.

        :returns: The json response from the server.

        """
        subreddit = six.text_type(subreddit)
        data = {'r': subreddit,
                'stylesheet_contents': stylesheet,
                'op': 'save'}  # Options: save / preview
        self.evict(self.config['stylesheet'].format(subreddit=subreddit))
        return self.request_json(self.config['subreddit_css'], data=data)

    @decorators.restrict_access(scope='modconfig')
    def upload_image(self, subreddit, image_path, name=None,
                     header=False, upload_as=None):
        """Upload an image to the subreddit.

        :param image_path: A path to the jpg or png image you want to upload.
        :param name: The name to provide the image. When None the name will be
            filename less any extension.
        :param header: When True, upload the image as the subreddit header.
        :param upload_as: Must be `'jpg'`, `'png'` or `None`. When None, this
            will match the format of the image itself. In all cases where both
            this value and the image format is not png, reddit will also
            convert  the image mode to RGBA. reddit optimizes the image
            according to this value.
        :returns: A link to the uploaded image. Raises an exception otherwise.

        """
        if name and header:
            raise TypeError('Both name and header cannot be set.')
        if upload_as not in (None, 'png', 'jpg'):
            raise TypeError("upload_as must be 'jpg', 'png', or None.")
        with open(image_path, 'rb') as image:
            image_type = upload_as or _image_type(image)
            data = {'r': six.text_type(subreddit), 'img_type': image_type}
            if header:
                data['header'] = 1
            else:
                if not name:
                    name = os.path.splitext(os.path.basename(image.name))[0]
                data['name'] = name

            response = json.loads(self._request(
                self.config['upload_image'], data=data, files={'file': image},
                method=to_native_string('POST'), retry_on_error=False))

        if response['errors']:
            raise errors.APIException(response['errors'], None)
        return response['img_src']

    def update_settings(self, subreddit, **kwargs):
        """Update only the given settings for the given subreddit.

        The settings to update must be given by keyword and match one of the
        parameter names in `set_settings`.

        :returns: The json response from the server.

        """
        settings = self.get_settings(subreddit)
        settings.update(kwargs)
        del settings['subreddit_id']
        return self.set_settings(subreddit, **settings)


class ModFlairMixin(AuthenticatedReddit):
    """Adds methods requiring the 'modflair' scope (or mod access).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='modflair')
    def add_flair_template(self, subreddit, text='', css_class='',
                           text_editable=False, is_link=False):
        """Add a flair template to the given subreddit.

        :returns: The json response from the server.

        """
        data = {'r': six.text_type(subreddit),
                'text': text,
                'css_class': css_class,
                'text_editable': six.text_type(text_editable),
                'flair_type': 'LINK_FLAIR' if is_link else 'USER_FLAIR'}
        return self.request_json(self.config['flairtemplate'], data=data)

    @decorators.restrict_access(scope='modflair')
    def clear_flair_templates(self, subreddit, is_link=False):
        """Clear flair templates for the given subreddit.

        :returns: The json response from the server.

        """
        data = {'r': six.text_type(subreddit),
                'flair_type': 'LINK_FLAIR' if is_link else 'USER_FLAIR'}
        return self.request_json(self.config['clearflairtemplates'], data=data)

    @decorators.restrict_access(scope='modflair')
    def configure_flair(self, subreddit, flair_enabled=False,
                        flair_position='right',
                        flair_self_assign=False,
                        link_flair_enabled=False,
                        link_flair_position='left',
                        link_flair_self_assign=False):
        """Configure the flair setting for the given subreddit.

        :returns: The json response from the server.

        """
        flair_enabled = 'on' if flair_enabled else 'off'
        flair_self_assign = 'on' if flair_self_assign else 'off'
        if not link_flair_enabled:
            link_flair_position = ''
        link_flair_self_assign = 'on' if link_flair_self_assign else 'off'
        data = {'r': six.text_type(subreddit),
                'flair_enabled': flair_enabled,
                'flair_position': flair_position,
                'flair_self_assign_enabled': flair_self_assign,
                'link_flair_position': link_flair_position,
                'link_flair_self_assign_enabled': link_flair_self_assign}
        return self.request_json(self.config['flairconfig'], data=data)

    @decorators.restrict_access(scope='modflair')
    def delete_flair(self, subreddit, user):
        """Delete the flair for the given user on the given subreddit.

        :returns: The json response from the server.

        """
        data = {'r': six.text_type(subreddit),
                'name': six.text_type(user)}
        return self.request_json(self.config['deleteflair'], data=data)

    @decorators.restrict_access(scope='modflair')
    def get_flair_list(self, subreddit, *args, **kwargs):
        """Return a get_content generator of flair mappings.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the flair list for.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url`, `root_field`, `thing_field`, and
        `after_field` parameters cannot be altered.

        """
        url = self.config['flairlist'].format(
            subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, root_field=None,
                                thing_field='users', after_field='next',
                                **kwargs)

    @decorators.restrict_access(scope='modflair')
    def set_flair(self, subreddit, item, flair_text='', flair_css_class=''):
        """Set flair for the user in the given subreddit.

        `item` can be a string, Redditor object, or Submission object.
        If `item` is a string it will be treated as the name of a Redditor.

        This method can only be called by a subreddit moderator with flair
        permissions. To set flair on yourself or your own links use
        :meth:`~praw.__init__.AuthenticatedReddit.select_flair`.

        :returns: The json response from the server.

        """
        data = {'r': six.text_type(subreddit),
                'text': flair_text or '',
                'css_class': flair_css_class or ''}
        if isinstance(item, objects.Submission):
            data['link'] = item.fullname
            evict = item.permalink
        else:
            data['name'] = six.text_type(item)
            evict = self.config['flairlist'].format(
                subreddit=six.text_type(subreddit))
        response = self.request_json(self.config['flair'], data=data)
        self.evict(evict)
        return response

    @decorators.restrict_access(scope='modflair')
    def set_flair_csv(self, subreddit, flair_mapping):
        """Set flair for a group of users in the given subreddit.

        flair_mapping should be a list of dictionaries with the following keys:
          `user`: the user name,
          `flair_text`: the flair text for the user (optional),
          `flair_css_class`: the flair css class for the user (optional)

        :returns: The json response from the server.

        """
        if not flair_mapping:
            raise errors.ClientException('flair_mapping must be set')
        item_order = ['user', 'flair_text', 'flair_css_class']
        lines = []
        for mapping in flair_mapping:
            if 'user' not in mapping:
                raise errors.ClientException('flair_mapping must '
                                             'contain `user` key')
            lines.append(','.join([mapping.get(x, '') for x in item_order]))
        response = []
        while len(lines):
            data = {'r': six.text_type(subreddit),
                    'flair_csv': '\n'.join(lines[:100])}
            response.extend(self.request_json(self.config['flaircsv'],
                                              data=data))
            lines = lines[100:]
        evict = self.config['flairlist'].format(
            subreddit=six.text_type(subreddit))
        self.evict(evict)
        return response


class ModLogMixin(AuthenticatedReddit):
    """Adds methods requiring the 'modlog' scope (or mod access).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='modlog')
    def get_mod_log(self, subreddit, mod=None, action=None, *args, **kwargs):
        """Return a get_content generator for moderation log items.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the modlog for.
        :param mod: If given, only return the actions made by this moderator.
            Both a moderator name or Redditor object can be used here.
        :param action: If given, only return entries for the specified action.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        params = kwargs.setdefault('params', {})
        if mod is not None:
            params['mod'] = six.text_type(mod)
        if action is not None:
            params['type'] = six.text_type(action)
        url = self.config['modlog'].format(subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)


class ModOnlyMixin(AuthenticatedReddit):
    """Adds methods requiring the logged in moderator access.

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    def _get_userlist(self, url, user_only, *args, **kwargs):
        content = self.get_content(url, *args, **kwargs)
        for data in content:
            user = objects.Redditor(self, data['name'], fetch=False)
            user.id = data['id'].split('_')[1]
            if user_only:
                yield user
            else:
                data['name'] = user
                yield data

    @decorators.restrict_access(scope='read', mod=True)
    def get_banned(self, subreddit, user_only=True, *args, **kwargs):
        """Return a get_content generator of banned users for the subreddit.

        :param subreddit: The subreddit to get the banned user list for.
        :param user_only: When False, the generator yields a dictionary of data
            associated with the server response for that user. In such cases,
            the Redditor will be in key 'name' (default: True).

        """
        url = self.config['banned'].format(subreddit=six.text_type(subreddit))
        return self._get_userlist(url, user_only, *args, **kwargs)

    def get_contributors(self, subreddit, *args, **kwargs):
        """
        Return a get_content generator of contributors for the given subreddit.

        If it's a public subreddit, then authentication as a
        moderator of the subreddit is required. For protected/private
        subreddits only access is required. See issue #246.

        """
        # pylint: disable=W0613
        def get_contributors_helper(self, subreddit):
            # It is necessary to have the 'self' argument as it's needed in
            # restrict_access to determine what class the decorator is
            # operating on.
            url = self.config['contributors'].format(
                subreddit=six.text_type(subreddit))
            return self._get_userlist(url, user_only=True, *args, **kwargs)

        if self.is_logged_in():
            if not isinstance(subreddit, objects.Subreddit):
                subreddit = self.get_subreddit(subreddit)
            if subreddit.subreddit_type == "public":
                decorator = decorators.restrict_access(scope='read', mod=True)
                return decorator(get_contributors_helper)(self, subreddit)
        return get_contributors_helper(self, subreddit)

    @decorators.restrict_access(scope='read', mod=True)
    def get_edited(self, subreddit='mod', *args, **kwargs):
        """Return a get_content generator of edited items.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the edited items for. Defaults to `mod` which
            includes items for all the subreddits you moderate.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['edited'].format(subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages', mod=True)
    def get_mod_mail(self, subreddit='mod', *args, **kwargs):
        """Return a get_content generator for moderator messages.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the moderator mail from. Defaults to `mod`
            which includes items for all the subreddits you moderate.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['mod_mail'].format(
            subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='read', mod=True)
    def get_mod_queue(self, subreddit='mod', *args, **kwargs):
        """Return a get_content generator for the moderator queue.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the modqueue for. Defaults to `mod` which
            includes items for all the subreddits you moderate.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['modqueue'].format(
            subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='read', mod=True)
    def get_muted(self, subreddit, user_only=True, *args, **kwargs):
        """Return a get_content generator for modmail-muted users.

        :param subreddit: Either a Subreddit object or the name of a subreddit
            to get the list of muted users from.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['muted'].format(subreddit=six.text_type(subreddit))
        return self._get_userlist(url, user_only, *args, **kwargs)

    @decorators.restrict_access(scope='read', mod=True)
    def get_reports(self, subreddit='mod', *args, **kwargs):
        """Return a get_content generator of reported items.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the reported items. Defaults to `mod` which
            includes items for all the subreddits you moderate.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['reports'].format(subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='read', mod=True)
    def get_spam(self, subreddit='mod', *args, **kwargs):
        """Return a get_content generator of spam-filtered items.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the spam-filtered items for. Defaults to `mod`
            which includes items for all the subreddits you moderate.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['spam'].format(subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access('modconfig', mod=False, login=False)
    def get_stylesheet(self, subreddit, **params):
        """Return the stylesheet and images for the given subreddit."""
        url = self.config['stylesheet'].format(
            subreddit=six.text_type(subreddit))
        return self.request_json(url, params=params)['data']

    @decorators.restrict_access(scope='read', mod=True)
    def get_unmoderated(self, subreddit='mod', *args, **kwargs):
        """Return a get_content generator of unmoderated submissions.

        :param subreddit: Either a Subreddit object or the name of the
            subreddit to return the unmoderated submissions for. Defaults to
            `mod` which includes items for all the subreddits you moderate.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        url = self.config['unmoderated'].format(
            subreddit=six.text_type(subreddit))
        return self.get_content(url, *args, **kwargs)

    @decorators.restrict_access(scope='read', mod=True)
    def get_wiki_banned(self, subreddit, *args, **kwargs):
        """Return a get_content generator of users banned from the wiki."""
        url = self.config['wiki_banned'].format(
            subreddit=six.text_type(subreddit))
        return self._get_userlist(url, user_only=True, *args, **kwargs)

    @decorators.restrict_access(scope='read', mod=True)
    def get_wiki_contributors(self, subreddit, *args, **kwargs):
        """Return a get_content generator of wiki contributors.

        The returned users are those who have been approved as a wiki
        contributor by the moderators of the subreddit, Whether or not they've
        actually contributed to the wiki is irrellevant, their approval as wiki
        contributors is all that matters.

        """
        url = self.config['wiki_contributors'].format(
            subreddit=six.text_type(subreddit))
        return self._get_userlist(url, user_only=True, *args, **kwargs)


class ModSelfMixin(AuthenticatedReddit):
    """Adds methods pertaining to the 'modself' OAuth scope (or login).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    def leave_contributor(self, subreddit):
        """Abdicate approved submitter status in a subreddit. Use with care.

        :param subreddit: The name of the subreddit to leave `status` from.

        :returns: the json response from the server.
        """
        return self._leave_status(subreddit, self.config['leavecontributor'])

    def leave_moderator(self, subreddit):
        """Abdicate moderator status in a subreddit. Use with care.

        :param subreddit: The name of the subreddit to leave `status` from.

        :returns: the json response from the server.
        """
        self.evict(self.config['my_mod_subreddits'])
        return self._leave_status(subreddit, self.config['leavemoderator'])

    @decorators.restrict_access(scope='modself', mod=False)
    def _leave_status(self, subreddit, statusurl):
        """Abdicate status in a subreddit.

        :param subreddit: The name of the subreddit to leave `status` from.
        :param statusurl: The API URL which will be used in the leave request.
            Please use :meth:`leave_contributor` or :meth:`leave_moderator`
            rather than setting this directly.

        :returns: the json response from the server.
        """
        if isinstance(subreddit, six.string_types):
            subreddit = self.get_subreddit(subreddit)

        data = {'id': subreddit.fullname}
        return self.request_json(statusurl, data=data)


class MultiredditMixin(AuthenticatedReddit):
    """Adds methods pertaining to multireddits.

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    MULTI_PATH = '/user/{0}/m/{1}'

    @decorators.restrict_access(scope='subscribe')
    def copy_multireddit(self, from_redditor, from_name, to_name=None,
                         *args, **kwargs):
        """Copy a multireddit.

        :param from_redditor: The username or Redditor object for the user
            who owns the original multireddit
        :param from_name: The name of the multireddit, belonging to
            from_redditor
        :param to_name: The name to copy the multireddit as. If None, uses
            the name of the original

        The additional parameters are passed directly into
        :meth:`~praw.__init__.BaseReddit.request_json`

        """
        if to_name is None:
            to_name = from_name

        from_multipath = self.MULTI_PATH.format(from_redditor, from_name)
        to_multipath = self.MULTI_PATH.format(self.user.name, to_name)
        data = {'display_name': to_name,
                'from': from_multipath,
                'to': to_multipath}
        return self.request_json(self.config['multireddit_copy'], data=data,
                                 *args, **kwargs)

    @decorators.restrict_access(scope='subscribe')
    def create_multireddit(self, name, description_md=None, icon_name=None,
                           key_color=None, subreddits=None, visibility=None,
                           weighting_scheme=None, overwrite=False,
                           *args, **kwargs):  # pylint: disable=W0613
        """Create a new multireddit.

        :param name: The name of the new multireddit.
        :param description_md: Optional description for the multireddit,
            formatted in markdown.
        :param icon_name: Optional, choose an icon name from this list: ``art
            and design``, ``ask``, ``books``, ``business``, ``cars``,
            ``comics``, ``cute animals``, ``diy``, ``entertainment``, ``food
            and drink``, ``funny``, ``games``, ``grooming``, ``health``, ``life
            advice``, ``military``, ``models pinup``, ``music``, ``news``,
            ``philosophy``, ``pictures and gifs``, ``science``, ``shopping``,
            ``sports``, ``style``, ``tech``, ``travel``, ``unusual stories``,
            ``video``, or ``None``.
        :param key_color: Optional rgb hex color code of the form `#xxxxxx`.
        :param subreddits: Optional list of subreddit names or Subreddit
            objects to initialize the Multireddit with. You can always
            add more later with
            :meth:`~praw.objects.Multireddit.add_subreddit`.
        :param visibility: Choose a privacy setting from this list:
            ``public``, ``private``, ``hidden``. Defaults to private if blank.
        :param weighting_scheme: Choose a weighting scheme from this list:
            ``classic``, ``fresh``. Defaults to classic if blank.
        :param overwrite: Allow for overwriting / updating multireddits.
            If False, and the multi name already exists, throw 409 error.
            If True, and the multi name already exists, use the given
            properties to update that multi.
            If True, and the multi name does not exist, create it normally.

        :returns: The newly created Multireddit object.

        The additional parameters are passed directly into
        :meth:`~praw.__init__.BaseReddit.request_json`

        """
        url = self.config['multireddit_about'].format(user=self.user.name,
                                                      multi=name)
        if subreddits:
            subreddits = [{'name': six.text_type(sr)} for sr in subreddits]
        model = {}
        for key in ('description_md', 'icon_name', 'key_color', 'subreddits',
                    'visibility', 'weighting_scheme'):
            value = locals()[key]
            if value:
                model[key] = value

        method = 'PUT' if overwrite else 'POST'
        return self.request_json(url, data={'model': json.dumps(model)},
                                 method=method, *args, **kwargs)

    @decorators.restrict_access(scope='subscribe')
    def delete_multireddit(self, name, *args, **kwargs):
        """Delete a Multireddit.

        Any additional parameters are passed directly into
        :meth:`~praw.__init__.BaseReddit.request`

        """
        url = self.config['multireddit_about'].format(user=self.user.name,
                                                      multi=name)

        # The modhash isn't necessary for OAuth requests
        if not self._use_oauth:
            self.http.headers['x-modhash'] = self.modhash

        try:
            self.request(url, data={}, method='DELETE', *args, **kwargs)
        finally:
            if not self._use_oauth:
                del self.http.headers['x-modhash']

    def edit_multireddit(self, *args, **kwargs):
        """Edit a multireddit, or create one if it doesn't already exist.

        See :meth:`create_multireddit` for accepted parameters.

        """
        return self.create_multireddit(*args, overwrite=True, **kwargs)

    def get_multireddit(self, redditor, multi, *args, **kwargs):
        """Return a Multireddit object for the author and name specified.

        :param redditor: The username or Redditor object of the user
            who owns the multireddit.
        :param multi: The name of the multireddit to fetch.

        The additional parameters are passed directly into the
        :class:`.Multireddit` constructor.

        """
        return objects.Multireddit(self, six.text_type(redditor), multi,
                                   *args, **kwargs)

    def get_multireddits(self, redditor, *args, **kwargs):
        """Return a list of multireddits belonging to a redditor.

        :param redditor: The username or Redditor object to find multireddits
            from.
        :returns: The json response from the server

        The additional parameters are passed directly into
        :meth:`~praw.__init__.BaseReddit.request_json`

        If the requested redditor is the current user, all multireddits
        are visible. Otherwise, only public multireddits are returned.

        """
        redditor = six.text_type(redditor)
        url = self.config['multireddit_user'].format(user=redditor)
        return self.request_json(url, *args, **kwargs)

    @decorators.restrict_access(scope='subscribe')
    def rename_multireddit(self, current_name, new_name, *args, **kwargs):
        """Rename a Multireddit.

        :param current_name: The name of the multireddit to rename
        :param new_name: The new name to assign to this multireddit

        The additional parameters are passed directly into
        :meth:`~praw.__init__.BaseReddit.request_json`

        """
        current_path = self.MULTI_PATH.format(self.user.name, current_name)
        new_path = self.MULTI_PATH.format(self.user.name, new_name)
        data = {'from': current_path,
                'to': new_path}
        return self.request_json(self.config['multireddit_rename'], data=data,
                                 *args, **kwargs)


class MySubredditsMixin(AuthenticatedReddit):
    """Adds methods requiring the 'mysubreddits' scope (or login).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='mysubreddits')
    def get_my_contributions(self, *args, **kwargs):
        """Return a get_content generator of subreddits.

        The Subreddits generated are those where the session's user is a
        contributor.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['my_con_subreddits'], *args,
                                **kwargs)

    @decorators.restrict_access(scope='mysubreddits')
    def get_my_moderation(self, *args, **kwargs):
        """Return a get_content generator of subreddits.

        The Subreddits generated are those where the session's user is a
        moderator.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['my_mod_subreddits'], *args,
                                **kwargs)

    @decorators.restrict_access(scope='mysubreddits')
    def get_my_multireddits(self):
        """Return a list of the authenticated Redditor's Multireddits."""
        # The JSON data for multireddits is returned from Reddit as a list
        # Therefore, we cannot use :meth:`get_content` to retrieve the objects
        return self.request_json(self.config['my_multis'])

    @decorators.restrict_access(scope='mysubreddits')
    def get_my_subreddits(self, *args, **kwargs):
        """Return a get_content generator of subreddits.

        The subreddits generated are those that hat the session's user is
        subscribed to.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['my_subreddits'], *args, **kwargs)


class PrivateMessagesMixin(AuthenticatedReddit):
    """Adds methods requiring the 'privatemessages' scope (or login).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='privatemessages')
    def _mark_as_read(self, thing_ids, unread=False):
        """Mark each of the supplied thing_ids as (un)read.

        :returns: The json response from the server.

        """
        data = {'id': ','.join(thing_ids)}
        key = 'unread_message' if unread else 'read_message'
        response = self.request_json(self.config[key], data=data)
        self.evict([self.config[x] for x in ['inbox', 'messages',
                                             'mod_mail', 'unread']])
        return response

    @decorators.restrict_access(scope='privatemessages')
    def get_comment_replies(self, *args, **kwargs):
        """Return a get_content generator for inboxed comment replies.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['comment_replies'],
                                *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    def get_inbox(self, *args, **kwargs):
        """Return a get_content generator for inbox (messages and comments).

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['inbox'], *args, **kwargs)

    def get_message(self, message_id, *args, **kwargs):
        """Return a Message object corresponding to the given ID.

        :param message_id: The ID or Fullname for a Message

        The additional parameters are passed directly into
        :meth:`~praw.objects.Message.from_id` of Message, and subsequently into
        :meth:`.request_json`.

        """
        return objects.Message.from_id(self, message_id, *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    def get_messages(self, *args, **kwargs):
        """Return a get_content generator for inbox (messages only).

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['messages'], *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    def get_post_replies(self, *args, **kwargs):
        """Return a get_content generator for inboxed submission replies.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['post_replies'], *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    def get_sent(self, *args, **kwargs):
        """Return a get_content generator for sent messages.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['sent'], *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    def get_unread(self, unset_has_mail=False, update_user=False, *args,
                   **kwargs):
        """Return a get_content generator for unread messages.

        :param unset_has_mail: When True, clear the has_mail flag (orangered)
            for the user.
        :param update_user: If both `unset_has_mail` and `update user` is True,
            set the `has_mail` attribute of the logged-in user to False.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        params = kwargs.setdefault('params', {})
        if unset_has_mail:
            params['mark'] = 'true'
            if update_user:  # Update the user object
                # Use setattr to avoid pylint error
                setattr(self.user, 'has_mail', False)
        return self.get_content(self.config['unread'], *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    def get_mentions(self, *args, **kwargs):
        """Return a get_content generator for username mentions.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        """
        return self.get_content(self.config['mentions'], *args, **kwargs)

    @decorators.restrict_access(scope='privatemessages')
    @decorators.require_captcha
    def send_message(self, recipient, subject, message, from_sr=None,
                     captcha=None, **kwargs):
        """Send a message to a redditor or a subreddit's moderators (mod mail).

        :param recipient: A Redditor or Subreddit instance to send a message
            to. A string can also be used in which case the string is treated
            as a redditor unless it is prefixed with either '/r/' or '#', in
            which case it will be treated as a subreddit.
        :param subject: The subject of the message to send.
        :param message: The actual message content.
        :param from_sr: A Subreddit instance or string to send the message
            from. When provided, messages are sent from the subreddit rather
            than from the authenticated user. Note that the authenticated user
            must be a moderator of the subreddit and have mail permissions.

        :returns: The json response from the server.

        This function may result in a captcha challenge. PRAW will
        automatically prompt you for a response. See :ref:`handling-captchas`
        if you want to manually handle captchas.

        """
        if isinstance(recipient, objects.Subreddit):
            recipient = '/r/{0}'.format(six.text_type(recipient))
        else:
            recipient = six.text_type(recipient)

        data = {'text': message,
                'subject': subject,
                'to': recipient}
        if from_sr:
            data['from_sr'] = six.text_type(from_sr)
        if captcha:
            data.update(captcha)
        response = self.request_json(self.config['compose'], data=data,
                                     retry_on_error=False)
        self.evict(self.config['sent'])
        return response


class ReportMixin(AuthenticatedReddit):
    """Adds methods requiring the 'report' scope (or login).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='report')
    def hide(self, thing_id, _unhide=False):
        """Hide one or multiple objects in the context of the logged in user.

        :param thing_id: A single fullname or list of fullnames,
            representing objects which will be hidden.
        :param _unhide: If True, unhide the object(s) instead. Use
            :meth:`~praw.__init__.ReportMixin.unhide` rather than setting this
            manually.

        :returns: The json response from the server.

        """
        if isinstance(thing_id, six.string_types):
            thing_id = [thing_id]
        else:
            # Guarantee a subscriptable type.
            thing_id = list(thing_id)

        if len(thing_id) == 0:
            raise ValueError('No fullnames provided')

        # Will we return a list of server responses, or just one?
        # TODO: In future versions, change the threshold to 1 to get
        # list-in-list-out, single-in-single-out behavior. Threshold of 50
        # is to avoid a breaking change at this time.
        return_list = len(thing_id) > 50

        id_chunks = chunk_sequence(thing_id, 50)
        responses = []
        for id_chunk in id_chunks:
            id_chunk = ','.join(id_chunk)

            method = 'unhide' if _unhide else 'hide'
            data = {'id': id_chunk,
                    'executed': method}

            response = self.request_json(self.config[method], data=data)
            responses.append(response)

            if self.user is not None:
                self.evict(urljoin(self.user._url,  # pylint: disable=W0212
                                   'hidden'))
        if return_list:
            return responses
        else:
            return responses[0]

    def unhide(self, thing_id):
        """Unhide up to 50 objects in the context of the logged in user.

        :param thing_id: A single fullname or list of fullnames,
            representing objects which will be unhidden.

        :returns: The json response from the server.

        """
        return self.hide(thing_id, _unhide=True)


class SubmitMixin(AuthenticatedReddit):
    """Adds methods requiring the 'submit' scope (or login).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    def _add_comment(self, thing_id, text):
        """Comment on the given thing with the given text.

        :returns: A Comment object for the newly created comment.

        """
        def add_comment_helper(self, thing_id, text):
            data = {'thing_id': thing_id,
                    'text': text}
            retval = self.request_json(self.config['comment'], data=data,
                                       retry_on_error=False)
            return retval

        if thing_id.startswith(self.config.by_object[objects.Message]):
            decorator = decorators.restrict_access(scope='privatemessages')
        else:
            decorator = decorators.restrict_access(scope='submit')
        retval = decorator(add_comment_helper)(self, thing_id, text)
        # REDDIT: reddit's end should only ever return a single comment
        return retval['data']['things'][0]

    @decorators.restrict_access(scope='submit')
    @decorators.require_captcha
    def submit(self, subreddit, title, text=None, url=None, captcha=None,
               save=None, send_replies=None, resubmit=None, **kwargs):
        """Submit a new link to the given subreddit.

        Accepts either a Subreddit object or a str containing the subreddit's
        display name.

        :param resubmit: If True, submit the link even if it has already been
            submitted.
        :param save: If True the new Submission will be saved after creation.
        :param send_replies: If True, inbox replies will be received when
            people comment on the submission. If set to None, the default of
            True for text posts and False for link posts will be used.

        :returns: The newly created Submission object if the reddit instance
            can access it. Otherwise, return the url to the submission.

        This function may result in a captcha challenge. PRAW will
        automatically prompt you for a response. See :ref:`handling-captchas`
        if you want to manually handle captchas.

        """
        if isinstance(text, six.string_types) == bool(url):
            raise TypeError('One (and only one) of text or url is required!')
        data = {'sr': six.text_type(subreddit),
                'title': title}
        if text or text == '':
            data['kind'] = 'self'
            data['text'] = text
        else:
            data['kind'] = 'link'
            data['url'] = url
        if captcha:
            data.update(captcha)
        if resubmit is not None:
            data['resubmit'] = resubmit
        if save is not None:
            data['save'] = save
        if send_replies is not None:
            data['sendreplies'] = send_replies
        result = self.request_json(self.config['submit'], data=data,
                                   retry_on_error=False)
        url = result['data']['url']
        # Clear the OAuth setting when attempting to fetch the submission
        if self._use_oauth:
            self._use_oauth = False
            if url.startswith(self.config.oauth_url):
                url = self.config.api_url + url[len(self.config.oauth_url):]
        try:
            return self.get_submission(url)
        except errors.Forbidden:
            # While the user may be able to submit to a subreddit,
            # that does not guarantee they have read access.
            return url


class SubscribeMixin(AuthenticatedReddit):
    """Adds methods requiring the 'subscribe' scope (or login).

    You should **not** directly instantiate instances of this class. Use
    :class:`.Reddit` instead.

    """

    @decorators.restrict_access(scope='subscribe')
    def subscribe(self, subreddit, unsubscribe=False):
        """Subscribe to the given subreddit.

        :param subreddit: Either the subreddit name or a subreddit object.
        :param unsubscribe: When True, unsubscribe.
        :returns: The json response from the server.

        """
        data = {'action': 'unsub' if unsubscribe else 'sub',
                'sr_name': six.text_type(subreddit)}
        response = self.request_json(self.config['subscribe'], data=data)
        self.evict(self.config['my_subreddits'])
        return response

    def unsubscribe(self, subreddit):
        """Unsubscribe from the given subreddit.

        :param subreddit: Either the subreddit name or a subreddit object.
        :returns: The json response from the server.

        """
        return self.subscribe(subreddit, unsubscribe=True)


class Reddit(ModConfigMixin, ModFlairMixin, ModLogMixin, ModOnlyMixin,
             ModSelfMixin, MultiredditMixin, MySubredditsMixin,
             PrivateMessagesMixin, ReportMixin, SubmitMixin, SubscribeMixin):
    """Provides access to reddit's API.

    See :class:`.BaseReddit`'s documentation for descriptions of the
    initialization parameters.

    """

# Prevent recursive import
from . import objects  # NOQA

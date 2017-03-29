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
Error classes.

Includes two main exceptions: ClientException, when something goes
wrong on our end, and APIExeception for when something goes wrong on the
server side. A number of classes extend these two main exceptions for more
specific exceptions.
"""

from __future__ import print_function, unicode_literals

import inspect
import six
import sys


class PRAWException(Exception):
    """The base PRAW Exception class.

    Ideally, this can be caught to handle any exception from PRAW.

    """


class ClientException(PRAWException):
    """Base exception class for errors that don't involve the remote API."""

    def __init__(self, message=None):
        """Construct a ClientException.

        :param message: The error message to display.

        """
        if not message:
            message = 'Clientside error'
        super(ClientException, self).__init__()
        self.message = message

    def __str__(self):
        """Return the message of the error."""
        return self.message


class OAuthScopeRequired(ClientException):
    """Indicates that an OAuth2 scope is required to make the function call.

    The attribute `scope` will contain the name of the necessary scope.

    """

    def __init__(self, function, scope, message=None):
        """Contruct an OAuthScopeRequiredClientException.

        :param function: The function that requires a scope.
        :param scope: The scope required for the function.
        :param message: A custom message to associate with the
            exception. Default: `function` requires the OAuth2 scope `scope`

        """
        if not message:
            message = '`{0}` requires the OAuth2 scope `{1}`'.format(function,
                                                                     scope)
        super(OAuthScopeRequired, self).__init__(message)
        self.scope = scope


class LoginRequired(ClientException):
    """Indicates that a logged in session is required.

    This exception is raised on a preemptive basis, whereas NotLoggedIn occurs
    in response to a lack of credentials on a privileged API call.

    """

    def __init__(self, function, message=None):
        """Construct a LoginRequired exception.

        :param function: The function that requires login-based authentication.
        :param message: A custom message to associate with the exception.
            Default: `function` requires a logged in session

        """
        if not message:
            message = '`{0}` requires a logged in session'.format(function)
        super(LoginRequired, self).__init__(message)


class LoginOrScopeRequired(OAuthScopeRequired, LoginRequired):
    """Indicates that either a logged in session or OAuth2 scope is required.

    The attribute `scope` will contain the name of the necessary scope.

    """

    def __init__(self, function, scope, message=None):
        """Construct a LoginOrScopeRequired exception.

        :param function: The function that requires authentication.
        :param scope: The scope that is required if not logged in.
        :param message: A custom message to associate with the exception.
            Default: `function` requires a logged in session or the OAuth2
            scope `scope`

        """
        if not message:
            message = ('`{0}` requires a logged in session or the '
                       'OAuth2 scope `{1}`').format(function, scope)
        super(LoginOrScopeRequired, self).__init__(function, scope, message)


class ModeratorRequired(LoginRequired):
    """Indicates that a moderator of the subreddit is required."""

    def __init__(self, function):
        """Construct a ModeratorRequired exception.

        :param function: The function that requires moderator access.

        """
        message = ('`{0}` requires a moderator '
                   'of the subreddit').format(function)
        super(ModeratorRequired, self).__init__(message)


class ModeratorOrScopeRequired(LoginOrScopeRequired, ModeratorRequired):
    """Indicates that a moderator of the sub or OAuth2 scope is required.

    The attribute `scope` will contain the name of the necessary scope.

    """

    def __init__(self, function, scope):
        """Construct a ModeratorOrScopeRequired exception.

        :param function: The function that requires moderator authentication or
            a moderator scope..
        :param scope: The scope that is required if not logged in with
            moderator access..

        """
        message = ('`{0}` requires a moderator of the subreddit or the '
                   'OAuth2 scope `{1}`').format(function, scope)
        super(ModeratorOrScopeRequired, self).__init__(function, scope,
                                                       message)


class OAuthAppRequired(ClientException):
    """Raised when an OAuth client cannot be initialized.

    This occurs when any one of the OAuth config values are not set.

    """


class HTTPException(PRAWException):
    """Base class for HTTP related exceptions."""

    def __init__(self, _raw, message=None):
        """Construct a HTTPException.

        :params _raw: The internal request library response object. This object
            is mapped to attribute `_raw` whose format may change at any time.

        """
        if not message:
            message = 'HTTP error'
        super(HTTPException, self).__init__()
        self._raw = _raw
        self.message = message

    def __str__(self):
        """Return the message of the error."""
        return self.message


class Forbidden(HTTPException):
    """Raised when the user does not have permission to the entity."""


class NotFound(HTTPException):
    """Raised when the requested entity is not found."""


class InvalidComment(PRAWException):
    """Indicate that the comment is no longer available on reddit."""

    ERROR_TYPE = 'DELETED_COMMENT'

    def __str__(self):
        """Return the message of the error."""
        return self.ERROR_TYPE


class InvalidSubmission(PRAWException):
    """Indicates that the submission is no longer available on reddit."""

    ERROR_TYPE = 'DELETED_LINK'

    def __str__(self):
        """Return the message of the error."""
        return self.ERROR_TYPE


class InvalidSubreddit(PRAWException):
    """Indicates that an invalid subreddit name was supplied."""

    ERROR_TYPE = 'SUBREDDIT_NOEXIST'

    def __str__(self):
        """Return the message of the error."""
        return self.ERROR_TYPE


class RedirectException(PRAWException):
    """Raised when a redirect response occurs that is not expected."""

    def __init__(self, request_url, response_url, message=None):
        """Construct a RedirectException.

        :param request_url: The url requested.
        :param response_url: The url being redirected to.
        :param message: A custom message to associate with the exception.

        """
        if not message:
            message = ('Unexpected redirect '
                       'from {0} to {1}').format(request_url, response_url)
        super(RedirectException, self).__init__()
        self.request_url = request_url
        self.response_url = response_url
        self.message = message

    def __str__(self):
        """Return the message of the error."""
        return self.message


class OAuthException(PRAWException):
    """Base exception class for OAuth API calls.

    Attribute `message` contains the error message.
    Attribute `url` contains the url that resulted in the error.

    """

    def __init__(self, message, url):
        """Construct a OAuthException.

        :param message: The message associated with the exception.
        :param url: The url that resulted in error.

        """
        super(OAuthException, self).__init__()
        self.message = message
        self.url = url

    def __str__(self):
        """Return the message along with the url."""
        return self.message + " on url {0}".format(self.url)


class OAuthInsufficientScope(OAuthException):
    """Raised when the current OAuth scope is not sufficient for the action.

    This indicates the access token is valid, but not for the desired action.

    """


class OAuthInvalidGrant(OAuthException):
    """Raised when the code to retrieve access information is not valid."""


class OAuthInvalidToken(OAuthException):
    """Raised when the current OAuth access token is not valid."""


class APIException(PRAWException):
    """Base exception class for the reddit API error message exceptions.

    All exceptions of this type should have their own subclass.

    """

    def __init__(self, error_type, message, field='', response=None):
        """Construct an APIException.

        :param error_type: The error type set on reddit's end.
        :param message: The associated message for the error.
        :param field: The input field associated with the error, or ''.
        :param response: The HTTP response that resulted in the exception.

        """
        super(APIException, self).__init__()
        self.error_type = error_type
        self.message = message
        self.field = field
        self.response = response

    def __str__(self):
        """Return a string containing the error message and field."""
        if hasattr(self, 'ERROR_TYPE'):
            return '`{0}` on field `{1}`'.format(self.message, self.field)
        else:
            return '({0}) `{1}` on field `{2}`'.format(self.error_type,
                                                       self.message,
                                                       self.field)


class ExceptionList(APIException):
    """Raised when more than one exception occurred."""

    def __init__(self, errors):
        """Construct an ExceptionList.

        :param errors: The list of errors.

        """
        super(ExceptionList, self).__init__(None, None)
        self.errors = errors

    def __str__(self):
        """Return a string representation for all the errors."""
        ret = '\n'
        for i, error in enumerate(self.errors):
            ret += '\tError {0}) {1}\n'.format(i, six.text_type(error))
        return ret


class AlreadySubmitted(APIException):
    """An exception to indicate that a URL was previously submitted."""

    ERROR_TYPE = 'ALREADY_SUB'


class AlreadyModerator(APIException):
    """Used to indicate that a user is already a moderator of a subreddit."""

    ERROR_TYPE = 'ALREADY_MODERATOR'


class BadCSS(APIException):
    """An exception to indicate bad CSS (such as invalid) was used."""

    ERROR_TYPE = 'BAD_CSS'


class BadCSSName(APIException):
    """An exception to indicate a bad CSS name (such as invalid) was used."""

    ERROR_TYPE = 'BAD_CSS_NAME'


class BadUsername(APIException):
    """An exception to indicate an invalid username was used."""

    ERROR_TYPE = 'BAD_USERNAME'


class InvalidCaptcha(APIException):
    """An exception for when an incorrect captcha error is returned."""

    ERROR_TYPE = 'BAD_CAPTCHA'


class InvalidEmails(APIException):
    """An exception for when invalid emails are provided."""

    ERROR_TYPE = 'BAD_EMAILS'


class InvalidFlairTarget(APIException):
    """An exception raised when an invalid user is passed as a flair target."""

    ERROR_TYPE = 'BAD_FLAIR_TARGET'


class InvalidInvite(APIException):
    """Raised when attempting to accept a nonexistent moderator invite."""

    ERROR_TYPE = 'NO_INVITE_FOUND'


class InvalidUser(APIException):
    """An exception for when a user doesn't exist."""

    ERROR_TYPE = 'USER_DOESNT_EXIST'


class InvalidUserPass(APIException):
    """An exception for failed logins."""

    ERROR_TYPE = 'WRONG_PASSWORD'


class InsufficientCreddits(APIException):
    """Raised when there are not enough creddits to complete the action."""

    ERROR_TYPE = 'INSUFFICIENT_CREDDITS'


class NotLoggedIn(APIException):
    """An exception for when a Reddit user isn't logged in."""

    ERROR_TYPE = 'USER_REQUIRED'


class NotModified(APIException):
    """An exception raised when reddit returns {'error': 304}.

    This error indicates that the requested content was not modified and is
    being requested too frequently. Such an error usually occurs when multiple
    instances of PRAW are running concurrently or in rapid succession.

    """

    def __init__(self, response):
        """Construct an instance of the NotModified exception.

        This error does not have an error_type, message, nor field.

        """
        super(NotModified, self).__init__(None, None, response=response)

    def __str__(self):
        """Return: That page has not been modified."""
        return 'That page has not been modified.'


class RateLimitExceeded(APIException):
    """An exception for when something has happened too frequently.

    Contains a `sleep_time` attribute for the number of seconds that must
    transpire prior to the next request.

    """

    ERROR_TYPE = 'RATELIMIT'

    def __init__(self, error_type, message, field, response):
        """Construct an instance of the RateLimitExceeded exception.

        The parameters match that of :class:`APIException`.

        The `sleep_time` attribute is extracted from the response object.

        """
        super(RateLimitExceeded, self).__init__(error_type, message,
                                                field, response)
        self.sleep_time = self.response['ratelimit']


class SubredditExists(APIException):
    """An exception to indicate that a subreddit name is not available."""

    ERROR_TYPE = 'SUBREDDIT_EXISTS'


class UsernameExists(APIException):
    """An exception to indicate that a username is not available."""

    ERROR_TYPE = 'USERNAME_TAKEN'


def _build_error_mapping():
    def predicate(obj):
        return inspect.isclass(obj) and hasattr(obj, 'ERROR_TYPE')

    tmp = {}
    for _, obj in inspect.getmembers(sys.modules[__name__], predicate):
        tmp[obj.ERROR_TYPE] = obj
    return tmp
ERROR_MAPPING = _build_error_mapping()

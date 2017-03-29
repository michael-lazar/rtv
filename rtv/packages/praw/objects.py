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
Contains code about objects such as Submissions, Redditors or Commments.

There are two main groups of objects in this file. The first are objects that
correspond to a Thing or part of a Thing as specified in reddit's API overview,
https://github.com/reddit/reddit/wiki/API. The second gives functionality that
extends over multiple Things. An object that extends from Saveable indicates
that it can be saved and unsaved in the context of a logged in user.
"""

from __future__ import print_function, unicode_literals
import six
from six.moves.urllib.parse import (  # pylint: disable=F0401
    parse_qs, urlparse, urlunparse)
from heapq import heappop, heappush
from json import dumps
from requests.compat import urljoin
from warnings import warn, warn_explicit
from praw import (AuthenticatedReddit as AR, ModConfigMixin as MCMix,
                  ModFlairMixin as MFMix, ModLogMixin as MLMix,
                  ModOnlyMixin as MOMix, ModSelfMixin as MSMix,
                  MultiredditMixin as MultiMix, PrivateMessagesMixin as PMMix,
                  SubmitMixin, SubscribeMixin, UnauthenticatedReddit as UR)
from praw.decorators import (alias_function, limit_chars, restrict_access,
                             deprecated)
from praw.errors import ClientException
from praw.internal import (_get_redditor_listing, _get_sorter,
                           _modify_relationship)


REDDITOR_KEYS = ('approved_by', 'author', 'banned_by', 'redditor',
                 'revision_by')


class RedditContentObject(object):
    """Base class that represents actual reddit objects."""

    @classmethod
    def from_api_response(cls, reddit_session, json_dict):
        """Return an instance of the appropriate class from the json_dict."""
        return cls(reddit_session, json_dict=json_dict)

    def __init__(self, reddit_session, json_dict=None, fetch=True,
                 info_url=None, underscore_names=None, uniq=None):
        """Create a new object from the dict of attributes returned by the API.

        The fetch parameter specifies whether to retrieve the object's
        information from the API (only matters when it isn't provided using
        json_dict).

        """
        self._info_url = info_url or reddit_session.config['info']
        self.reddit_session = reddit_session
        self._underscore_names = underscore_names
        self._uniq = uniq
        self._has_fetched = self._populate(json_dict, fetch)

    def __eq__(self, other):
        """Return whether the other instance equals the current."""
        return (isinstance(other, RedditContentObject) and
                self.fullname == other.fullname)

    def __hash__(self):
        """Return the hash of the current instance."""
        return hash(self.fullname)

    def __getattr__(self, attr):
        """Return the value of the `attr` attribute."""
        # Because this method may perform web requests, there are certain
        # attributes we must blacklist to prevent accidental requests:
        # __members__, __methods__: Caused by `dir(obj)` in Python 2.
        # __setstate__: Caused by Pickle deserialization.
        blacklist = ('__members__', '__methods__', '__setstate__')
        if attr not in blacklist and not self._has_fetched:
            self._has_fetched = self._populate(None, True)
            return getattr(self, attr)
        msg = '\'{0}\' has no attribute \'{1}\''.format(type(self), attr)
        raise AttributeError(msg)

    def __getstate__(self):
        """Needed for `pickle`.

        Without this, pickle protocol version 0 will make HTTP requests
        upon serialization, hence slowing it down significantly.
        """
        return self.__dict__

    def __ne__(self, other):
        """Return whether the other instance differs from the current."""
        return not self == other

    def __reduce_ex__(self, _):
        """Needed for `pickle`.

        Without this, `pickle` protocol version 2 will make HTTP requests
        upon serialization, hence slowing it down significantly.
        """
        return self.__reduce__()

    def __setattr__(self, name, value):
        """Set the `name` attribute to `value."""
        if value and name == 'subreddit':
            value = Subreddit(self.reddit_session, value, fetch=False)
        elif value and name in REDDITOR_KEYS:
            if isinstance(value, bool):
                pass
            elif isinstance(value, dict):
                value = Redditor(self.reddit_session, json_dict=value['data'])
            elif not value or value == '[deleted]':
                value = None
            else:
                value = Redditor(self.reddit_session, value, fetch=False)
        object.__setattr__(self, name, value)

    def __str__(self):
        """Return a string representation of the RedditContentObject."""
        retval = self.__unicode__()
        if not six.PY3:
            retval = retval.encode('utf-8')
        return retval

    def _get_json_dict(self):
        # (disabled for entire function) pylint: disable=W0212

        # OAuth handling needs to be special cased here. For instance, the user
        # might be calling a method on a Subreddit object that requires first
        # loading the information about the subreddit. This method should try
        # to obtain the information in a scope-less manner unless either:
        # a) The object is a WikiPage and the reddit_session has the `wikiread`
        #    scope.
        # b) The object is not a WikiPage and the reddit_session has the
        #    `read` scope.
        prev_use_oauth = self.reddit_session._use_oauth

        wiki_page = isinstance(self, WikiPage)
        scope = self.reddit_session.has_scope

        self.reddit_session._use_oauth = wiki_page and scope('wikiread') or \
            not wiki_page and scope('read')

        try:
            params = {'uniq': self._uniq} if self._uniq else {}
            response = self.reddit_session.request_json(
                self._info_url, params=params, as_objects=False)
        finally:
            self.reddit_session._use_oauth = prev_use_oauth
        return response['data']

    def _populate(self, json_dict, fetch):
        if json_dict is None:
            json_dict = self._get_json_dict() if fetch else {}

        if self.reddit_session.config.store_json_result is True:
            self.json_dict = json_dict
        else:
            self.json_dict = None

        # TODO: Remove this wikipagelisting hack
        if isinstance(json_dict, list):
            json_dict = {'_tmp': json_dict}

        for name, value in six.iteritems(json_dict):
            if self._underscore_names and name in self._underscore_names:
                name = '_' + name
            setattr(self, name, value)

        self._post_populate(fetch)
        return bool(json_dict) or fetch

    def _post_populate(self, fetch):
        """Called after populating the attributes of the instance."""

    @property
    def fullname(self):
        """Return the object's fullname.

        A fullname is an object's kind mapping like `t3` followed by an
        underscore and the object's base36 id, e.g., `t1_c5s96e0`.

        """
        by_object = self.reddit_session.config.by_object
        return '{0}_{1}'.format(by_object[self.__class__], self.id)

    @property
    @deprecated('``has_fetched`` will not be a public attribute in PRAW4.')
    def has_fetched(self):
        """Return whether the object has been fully fetched from reddit."""
        return self._has_fetched


class Moderatable(RedditContentObject):
    """Interface for Reddit content objects that have can be moderated."""

    @restrict_access(scope='modposts')
    def approve(self):
        """Approve object.

        This reverts a removal, resets the report counter, marks it with a
        green check mark (only visible to other moderators) on the website view
        and sets the approved_by attribute to the logged in user.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['approve']
        data = {'id': self.fullname}
        response = self.reddit_session.request_json(url, data=data)
        urls = [self.reddit_session.config[x] for x in ['modqueue', 'spam']]
        if isinstance(self, Submission):
            urls += self.subreddit._listing_urls  # pylint: disable=W0212
        self.reddit_session.evict(urls)
        return response

    @restrict_access(scope='modposts')
    def distinguish(self, as_made_by='mod', sticky=False):
        """Distinguish object as made by mod, admin or special.

        Distinguished objects have a different author color. With Reddit
        Enhancement Suite it is the background color that changes.

        `sticky` argument only used for top-level Comments.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['distinguish']
        data = {'id': self.fullname,
                'how': 'yes' if as_made_by == 'mod' else as_made_by}
        if isinstance(self, Comment) and self.is_root:
            data['sticky'] = sticky
        return self.reddit_session.request_json(url, data=data)

    @restrict_access(scope='modposts')
    def ignore_reports(self):
        """Ignore future reports on this object.

        This prevents future reports from causing notifications or appearing
        in the various moderation listing. The report count will still
        increment.

        """
        url = self.reddit_session.config['ignore_reports']
        data = {'id': self.fullname}
        return self.reddit_session.request_json(url, data=data)

    @restrict_access(scope='modposts')
    def remove(self, spam=False):
        """Remove object. This is the moderator version of delete.

        The object is removed from the subreddit listings and placed into the
        spam listing. If spam is set to True, then the automatic spam filter
        will try to remove objects with similar attributes in the future.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['remove']
        data = {'id': self.fullname,
                'spam': 'True' if spam else 'False'}
        response = self.reddit_session.request_json(url, data=data)
        urls = [self.reddit_session.config[x] for x in ['modqueue', 'spam']]
        if isinstance(self, Submission) and hasattr(self, 'subreddit'):
            urls += self.subreddit._listing_urls  # pylint: disable=W0212
        self.reddit_session.evict(urls)
        return response

    def undistinguish(self):
        """Remove mod, admin or special distinguishing on object.

        :returns: The json response from the server.

        """
        return self.distinguish(as_made_by='no')

    @restrict_access(scope='modposts')
    def unignore_reports(self):
        """Remove ignoring of future reports on this object.

        Undoes 'ignore_reports'. Future reports will now cause notifications
        and appear in the various moderation listings.

        """
        url = self.reddit_session.config['unignore_reports']
        data = {'id': self.fullname}
        return self.reddit_session.request_json(url, data=data)


class Editable(RedditContentObject):
    """Interface for Reddit content objects that can be edited and deleted."""

    @restrict_access(scope='edit')
    def delete(self):
        """Delete this object.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['del']
        data = {'id': self.fullname}
        response = self.reddit_session.request_json(url, data=data)
        self.reddit_session.evict(self.reddit_session.config['user'])
        return response

    @restrict_access(scope='edit')
    def edit(self, text):
        """Replace the body of the object with `text`.

        :returns: The updated object.

        """
        url = self.reddit_session.config['edit']
        data = {'thing_id': self.fullname,
                'text': text}
        response = self.reddit_session.request_json(url, data=data)
        self.reddit_session.evict(self.reddit_session.config['user'])
        return response['data']['things'][0]


class Gildable(RedditContentObject):
    """Interface for RedditContentObjects that can be gilded."""

    @restrict_access(scope='creddits', oauth_only=True)
    def gild(self, months=None):
        """Gild the Redditor or author of the content.

        :param months: Specifies the number of months to gild. This parameter
            is Only valid when the instance called upon is of type
            Redditor. When not provided, the value defaults to 1.
        :returns: True on success, otherwise raises an exception.

        """
        if isinstance(self, Redditor):
            months = int(months) if months is not None else 1
            if months < 1:
                raise TypeError('months must be at least 1')
            if months > 36:
                raise TypeError('months must be no more than 36')
            response = self.reddit_session.request(
                self.reddit_session.config['gild_user'].format(
                    username=six.text_type(self)), data={'months': months})
        elif months is not None:
            raise TypeError('months is not a valid parameter for {0}'
                            .format(type(self)))
        else:
            response = self.reddit_session.request(
                self.reddit_session.config['gild_thing']
                .format(fullname=self.fullname), data=True)
        return response.status_code == 200


class Hideable(RedditContentObject):
    """Interface for objects that can be hidden."""

    def hide(self, _unhide=False):
        """Hide object in the context of the logged in user.

        :param _unhide: If True, unhide the item instead.  Use
            :meth:`~praw.objects.Hideable.unhide` instead of setting this
            manually.

        :returns: The json response from the server.

        """
        return self.reddit_session.hide(self.fullname, _unhide=_unhide)

    def unhide(self):
        """Unhide object in the context of the logged in user.

        :returns: The json response from the server.

        """
        return self.hide(_unhide=True)


class Inboxable(RedditContentObject):
    """Interface for objects that appear in the inbox (orangereds)."""

    def mark_as_read(self):
        """Mark object as read.

        :returns: The json response from the server.

        """
        return self.reddit_session._mark_as_read([self.fullname])

    def mark_as_unread(self):
        """Mark object as unread.

        :returns: The json response from the server.

        """
        return self.reddit_session._mark_as_read([self.fullname], unread=True)

    def reply(self, text):
        """Reply to object with the specified text.

        :returns: A Comment object for the newly created comment (reply).

        """
        # pylint: disable=W0212
        response = self.reddit_session._add_comment(self.fullname, text)
        # pylint: enable=W0212
        urls = [self.reddit_session.config['inbox']]
        if isinstance(self, Comment):
            urls.append(self.submission._api_link)  # pylint: disable=W0212
        elif isinstance(self, Message):
            urls.append(self.reddit_session.config['sent'])
        self.reddit_session.evict(urls)
        return response


class Messageable(RedditContentObject):
    """Interface for RedditContentObjects that can be messaged."""

    _methods = (('send_message', PMMix),)


class Refreshable(RedditContentObject):
    """Interface for objects that can be refreshed."""

    def refresh(self):
        """Re-query to update object with latest values. Return the object.

        Any listing, such as the submissions on a subreddits top page, will
        automatically be refreshed serverside. Refreshing a submission will
        also refresh all its comments.

        In the rare case of a comment being deleted or removed when it had
        no replies, a second request will be made, not all information will
        be updated and a warning will list the attributes that could not be
        retrieved if there were any.

        """
        unique = self.reddit_session._unique_count  # pylint: disable=W0212
        self.reddit_session._unique_count += 1  # pylint: disable=W0212

        if isinstance(self, Redditor):
            other = Redditor(self.reddit_session, self._case_name, fetch=True,
                             uniq=unique)
        elif isinstance(self, Comment):
            sub = Submission.from_url(self.reddit_session, self.permalink,
                                      params={'uniq': unique})
            if sub.comments:
                other = sub.comments[0]
            else:
                # comment is "specially deleted", a reddit inconsistency;
                # see #519, #524, #535, #537, and #552 it needs to be
                # retreived via /api/info, but that's okay since these
                # specially deleted comments always have the same json
                # structure. The unique count needs to be updated
                # in case the comment originally came from /api/info
                msg = ("Comment {0} was deleted or removed, and had "
                       "no replies when such happened, so a second "
                       "request was made to /api/info.".format(self.name))
                unique = self.reddit_session._unique_count
                self.reddit_session._unique_count += 1
                other = self.reddit_session.get_info(thing_id=self.name,
                                                     params={'uniq': unique})
                oldkeys = set(self.__dict__.keys())
                newkeys = set(other.__dict__.keys())
                keydiff = ", ".join(oldkeys - newkeys)
                if keydiff:
                    msg += "\nCould not retrieve:\n{0}".format(keydiff)
                self.__dict__.update(other.__dict__)  # pylint: disable=W0201
                warn(msg, RuntimeWarning)
                return self
        elif isinstance(self, Multireddit):
            other = Multireddit(self.reddit_session, author=self._author,
                                name=self.name, uniq=unique, fetch=True)
        elif isinstance(self, Submission):
            params = self._params.copy()
            params['uniq'] = unique
            other = Submission.from_url(self.reddit_session, self.permalink,
                                        comment_sort=self._comment_sort,
                                        params=params)
        elif isinstance(self, Subreddit):
            other = Subreddit(self.reddit_session, self._case_name, fetch=True,
                              uniq=unique)
        elif isinstance(self, WikiPage):
            other = WikiPage(self.reddit_session,
                             six.text_type(self.subreddit), self.page,
                             fetch=True, uniq=unique)

        self.__dict__ = other.__dict__  # pylint: disable=W0201
        return self


class Reportable(RedditContentObject):
    """Interface for RedditContentObjects that can be reported."""

    @restrict_access(scope='report')
    def report(self, reason=None):
        """Report this object to the moderators.

        :param reason: The user-supplied reason for reporting a comment
            or submission. Default: None (blank reason)
        :returns: The json response from the server.

        """
        url = self.reddit_session.config['report']
        data = {'id': self.fullname}
        if reason:
            data['reason'] = reason
        response = self.reddit_session.request_json(url, data=data)
        # Reported objects are automatically hidden as well
        # pylint: disable=W0212
        self.reddit_session.evict(
            [self.reddit_session.config['user'],
             urljoin(self.reddit_session.user._url, 'hidden')])
        # pylint: enable=W0212
        return response


class Saveable(RedditContentObject):
    """Interface for RedditContentObjects that can be saved."""

    @restrict_access(scope='save')
    def save(self, unsave=False):
        """Save the object.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['unsave' if unsave else 'save']
        data = {'id': self.fullname,
                'executed': 'unsaved' if unsave else 'saved'}
        response = self.reddit_session.request_json(url, data=data)
        self.reddit_session.evict(self.reddit_session.config['saved'])
        return response

    def unsave(self):
        """Unsave the object.

        :returns: The json response from the server.

        """
        return self.save(unsave=True)


class Voteable(RedditContentObject):
    """Interface for RedditContentObjects that can be voted on."""

    def clear_vote(self):
        """Remove the logged in user's vote on the object.

        Running this on an object with no existing vote has no adverse effects.

        Note: votes must be cast by humans. That is, API clients proxying a
        human's action one-for-one are OK, but bots deciding how to vote on
        content or amplifying a human's vote are not. See the reddit rules for
        more details on what constitutes vote cheating.

        Source for note: http://www.reddit.com/dev/api#POST_api_vote

        :returns: The json response from the server.

        """
        return self.vote()

    def downvote(self):
        """Downvote object. If there already is a vote, replace it.

        Note: votes must be cast by humans. That is, API clients proxying a
        human's action one-for-one are OK, but bots deciding how to vote on
        content or amplifying a human's vote are not. See the reddit rules for
        more details on what constitutes vote cheating.

        Source for note: http://www.reddit.com/dev/api#POST_api_vote

        :returns: The json response from the server.

        """
        return self.vote(direction=-1)

    def upvote(self):
        """Upvote object. If there already is a vote, replace it.

        Note: votes must be cast by humans. That is, API clients proxying a
        human's action one-for-one are OK, but bots deciding how to vote on
        content or amplifying a human's vote are not. See the reddit rules for
        more details on what constitutes vote cheating.

        Source for note: http://www.reddit.com/dev/api#POST_api_vote

        :returns: The json response from the server.

        """
        return self.vote(direction=1)

    @restrict_access(scope='vote')
    def vote(self, direction=0):
        """Vote for the given item in the direction specified.

        Note: votes must be cast by humans. That is, API clients proxying a
        human's action one-for-one are OK, but bots deciding how to vote on
        content or amplifying a human's vote are not. See the reddit rules for
        more details on what constitutes vote cheating.

        Source for note: http://www.reddit.com/dev/api#POST_api_vote

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['vote']
        data = {'id': self.fullname,
                'dir': six.text_type(direction)}
        if self.reddit_session.user:
            # pylint: disable=W0212
            urls = [urljoin(self.reddit_session.user._url, 'disliked'),
                    urljoin(self.reddit_session.user._url, 'liked')]
            # pylint: enable=W0212
            self.reddit_session.evict(urls)
        return self.reddit_session.request_json(url, data=data)


class Comment(Editable, Gildable, Inboxable, Moderatable, Refreshable,
              Reportable, Saveable, Voteable):
    """A class that represents a reddit comments."""

    def __init__(self, reddit_session, json_dict):
        """Construct an instance of the Comment object."""
        super(Comment, self).__init__(reddit_session, json_dict,
                                      underscore_names=['replies'])
        self._has_fetched_replies = not hasattr(self, 'was_comment')
        if self._replies:
            self._replies = self._replies['data']['children']
        elif self._replies == '':  # Comment tree was built and there are none
            self._replies = []
        else:
            self._replies = None
        self._submission = None

    @limit_chars
    def __unicode__(self):
        """Return a string representation of the comment."""
        return getattr(self, 'body', '[Unloaded Comment]')

    @property
    def _fast_permalink(self):
        """Return the short permalink to the comment."""
        if hasattr(self, 'link_id'):  # from /r or /u comments page
            sid = self.link_id.split('_')[1]
        else:  # from user's /message page
            sid = self.context.split('/')[4]
        return urljoin(self.reddit_session.config['comments'], '{0}/_/{1}'
                       .format(sid, self.id))

    def _update_submission(self, submission):
        """Submission isn't set on __init__ thus we need to update it."""
        submission._comments_by_id[self.name] = self  # pylint: disable=W0212
        self._submission = submission
        if self._replies:
            for reply in self._replies:
                reply._update_submission(submission)  # pylint: disable=W0212

    @property
    def is_root(self):
        """Return True when the comment is a top level comment."""
        sub_prefix = self.reddit_session.config.by_object[Submission]
        return self.parent_id.startswith(sub_prefix)

    @property
    def permalink(self):
        """Return a permalink to the comment."""
        return urljoin(self.submission.permalink, self.id)

    @property
    def replies(self):
        """Return a list of the comment replies to this comment.

        If the comment is not from a submission, :meth:`replies` will
        always be an empty list unless you call :meth:`refresh()
        before calling :meth:`replies` due to a limitation in
        reddit's API.

        """
        if self._replies is None or not self._has_fetched_replies:
            response = self.reddit_session.request_json(self._fast_permalink)
            if response[1]['data']['children']:
                # pylint: disable=W0212
                self._replies = response[1]['data']['children'][0]._replies
            else:
                # comment is "specially deleted", a reddit inconsistency;
                # see #519, #524, #535, #537, and #552 it needs to be
                # retreived via /api/info, but that's okay since these
                # specially deleted comments always have the same json
                # structure.
                msg = ("Comment {0} was deleted or removed, and had "
                       "no replies when such happened, so it still "
                       "has no replies".format(self.name))
                warn(msg, RuntimeWarning)
                self._replies = []
            # pylint: enable=W0212
            self._has_fetched_replies = True
            # Set the submission object if it is not set.
            if not self._submission:
                self._submission = response[0]['data']['children'][0]
        return self._replies

    @property
    def submission(self):
        """Return the Submission object this comment belongs to."""
        if not self._submission:  # Comment not from submission
            self._submission = self.reddit_session.get_submission(
                url=self._fast_permalink)
        return self._submission


class Message(Inboxable):
    """A class for private messages."""

    @staticmethod
    @restrict_access(scope='privatemessages')
    def from_id(reddit_session, message_id, *args, **kwargs):
        """Request the url for a Message and return a Message object.

        :param reddit_session: The session to make the request with.
        :param message_id: The ID of the message to request.

        The additional parameters are passed directly into
        :meth:`.request_json`.

        """
        # Reduce fullname to ID if necessary
        message_id = message_id.split('_', 1)[-1]
        url = reddit_session.config['message'].format(messageid=message_id)
        message_info = reddit_session.request_json(url, *args, **kwargs)
        message = message_info['data']['children'][0]

        # Messages are received as a listing such that
        # the first item is always the thread's root.
        # The ID requested by the user may be a child.
        if message.id == message_id:
            return message
        for child in message.replies:
            if child.id == message_id:
                return child

    def __init__(self, reddit_session, json_dict):
        """Construct an instance of the Message object."""
        super(Message, self).__init__(reddit_session, json_dict)
        if self.replies:  # pylint: disable=E0203
            self.replies = self.replies['data']['children']
        else:
            self.replies = []

    @limit_chars
    def __unicode__(self):
        """Return a string representation of the Message."""
        return 'From: {0}\nSubject: {1}\n\n{2}'.format(self.author,
                                                       self.subject, self.body)

    @restrict_access(scope='privatemessages')
    def collapse(self):
        """Collapse a private message or modmail."""
        url = self.reddit_session.config['collapse_message']
        self.reddit_session.request_json(url, data={'id': self.name})

    @restrict_access(scope='modcontributors')
    def mute_modmail_author(self, _unmute=False):
        """Mute the sender of this modmail message.

        :param _unmute: Unmute the user instead. Please use
            :meth:`unmute_modmail_author` instead of setting this directly.

        """
        path = 'unmute_sender' if _unmute else 'mute_sender'
        return self.reddit_session.request_json(
            self.reddit_session.config[path], data={'id': self.fullname})

    @restrict_access(scope='privatemessages')
    def uncollapse(self):
        """Uncollapse a private message or modmail."""
        url = self.reddit_session.config['uncollapse_message']
        self.reddit_session.request_json(url, data={'id': self.name})

    def unmute_modmail_author(self):
        """Unmute the sender of this modmail message."""
        return self.mute_modmail_author(_unmute=True)


class MoreComments(RedditContentObject):
    """A class indicating there are more comments."""

    def __init__(self, reddit_session, json_dict):
        """Construct an instance of the MoreComment object."""
        super(MoreComments, self).__init__(reddit_session, json_dict)
        self.submission = None
        self._comments = None

    def __lt__(self, other):
        """Proide a sort order on the MoreComments object."""
        # To work with heapq a "smaller" item is the one with the most comments
        # We are intentionally making the biggest element the smallest element
        # to turn the min-heap implementation in heapq into a max-heap
        # implementation for Submission.replace_more_comments()
        return self.count > other.count

    def __unicode__(self):
        """Return a string representation of the MoreComments object."""
        return '[More Comments: {0}]'.format(self.count)

    def _continue_comments(self, update):
        assert len(self.children) > 0
        tmp = self.reddit_session.get_submission(urljoin(
            self.submission.permalink, self.parent_id.split('_', 1)[1]))
        assert len(tmp.comments) == 1
        self._comments = tmp.comments[0].replies
        if update:
            for comment in self._comments:
                # pylint: disable=W0212
                comment._update_submission(self.submission)
                # pylint: enable=W0212
        return self._comments

    def _update_submission(self, submission):
        self.submission = submission

    def comments(self, update=True):
        """Fetch and return the comments for a single MoreComments object."""
        if not self._comments:
            if self.count == 0:  # Handle 'continue this thread' type
                return self._continue_comments(update)
            # pylint: disable=W0212
            children = [x for x in self.children if 't1_{0}'.format(x)
                        not in self.submission._comments_by_id]
            # pylint: enable=W0212
            if not children:
                return None
            data = {'children': ','.join(children),
                    'link_id': self.submission.fullname,
                    'r': str(self.submission.subreddit)}

            # pylint: disable=W0212
            if self.submission._comment_sort:
                data['where'] = self.submission._comment_sort
            # pylint: enable=W0212
            url = self.reddit_session.config['morechildren']
            response = self.reddit_session.request_json(url, data=data)
            self._comments = response['data']['things']
            if update:
                for comment in self._comments:
                    # pylint: disable=W0212
                    comment._update_submission(self.submission)
                    # pylint: enable=W0212
        return self._comments


class Redditor(Gildable, Messageable, Refreshable):
    """A class representing the users of reddit."""

    _methods = (('get_multireddit', MultiMix), ('get_multireddits', MultiMix))

    get_comments = _get_redditor_listing('comments')
    get_overview = _get_redditor_listing('')
    get_submitted = _get_redditor_listing('submitted')

    def __init__(self, reddit_session, user_name=None, json_dict=None,
                 fetch=False, **kwargs):
        """Construct an instance of the Redditor object."""
        if not user_name:
            user_name = json_dict['name']
        info_url = reddit_session.config['user_about'].format(user=user_name)
        # name is set before calling the parent constructor so that the
        # json_dict 'name' attribute (if available) has precedence
        self._case_name = user_name
        super(Redditor, self).__init__(reddit_session, json_dict,
                                       fetch, info_url, **kwargs)
        self.name = self._case_name
        self._url = reddit_session.config['user'].format(user=self.name)
        self._mod_subs = None

    def __repr__(self):
        """Return a code representation of the Redditor."""
        return 'Redditor(user_name=\'{0}\')'.format(self.name)

    def __unicode__(self):
        """Return a string representation of the Redditor."""
        return self.name

    def _post_populate(self, fetch):
        if fetch:
            # Maintain a consistent `name` until the user
            # explicitly calls `redditor.refresh()`
            tmp = self._case_name
            self._case_name = self.name
            self.name = tmp

    @restrict_access(scope='subscribe')
    def friend(self, note=None, _unfriend=False):
        """Friend the user.

        :param note: A personal note about the user. Requires reddit Gold.
        :param _unfriend: Unfriend the user. Please use :meth:`unfriend`
            instead of setting this parameter manually.

        :returns: The json response from the server.

        """
        self.reddit_session.evict(self.reddit_session.config['friends'])

        # Requests through password auth use /api/friend
        # Requests through oauth use /api/v1/me/friends/{username}
        if not self.reddit_session.is_oauth_session():
            modifier = _modify_relationship('friend', unlink=_unfriend)
            data = {'note': note} if note else {}
            return modifier(self.reddit_session.user, self, **data)

        url = self.reddit_session.config['friend_v1'].format(user=self.name)
        # This endpoint wants the data to be a string instead of an actual
        # dictionary, although it is not required to have any content for adds.
        # Unfriending does require the 'id' key.
        if _unfriend:
            data = {'id': self.name}
        else:
            # We cannot send a null or empty note string.
            data = {'note': note} if note else {}
        data = dumps(data)
        method = 'DELETE' if _unfriend else 'PUT'
        return self.reddit_session.request_json(url, data=data, method=method)

    def get_disliked(self, *args, **kwargs):
        """Return a listing of the Submissions the user has downvoted.

        This method points to :meth:`get_downvoted`, as the "disliked" name
        is being phased out.
        """
        return self.get_downvoted(*args, **kwargs)

    def get_downvoted(self, *args, **kwargs):
        """Return a listing of the Submissions the user has downvoted.

        :returns: get_content generator of Submission items.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        As a default, this listing is only accessible by the user. Thereby
        requiring either user/pswd authentication or OAuth authentication with
        the 'history' scope. Users may choose to make their voting record
        public by changing a user preference. In this case, no authentication
        will be needed to access this listing.

        """
        # Sending an OAuth authenticated request for a redditor, who isn't the
        # authenticated user. But who has a public voting record will be
        # successful.
        kwargs['_use_oauth'] = self.reddit_session.is_oauth_session()
        return _get_redditor_listing('downvoted')(self, *args, **kwargs)

    @restrict_access(scope='mysubreddits')
    def get_friend_info(self):
        """Return information about this friend, including personal notes.

        The personal note can be added or overwritten with :meth:friend, but
            only if the user has reddit Gold.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['friend_v1'].format(user=self.name)
        data = {'id': self.name}
        return self.reddit_session.request_json(url, data=data, method='GET')

    def get_liked(self, *args, **kwargs):
        """Return a listing of the Submissions the user has upvoted.

        This method points to :meth:`get_upvoted`, as the "liked" name
        is being phased out.
        """
        return self.get_upvoted(*args, **kwargs)

    def get_upvoted(self, *args, **kwargs):
        """Return a listing of the Submissions the user has upvoted.

        :returns: get_content generator of Submission items.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` parameter cannot be altered.

        As a default, this listing is only accessible by the user. Thereby
        requirering either user/pswd authentication or OAuth authentication
        with the 'history' scope. Users may choose to make their voting record
        public by changing a user preference. In this case, no authentication
        will be needed to access this listing.

        """
        kwargs['_use_oauth'] = self.reddit_session.is_oauth_session()
        return _get_redditor_listing('upvoted')(self, *args, **kwargs)

    def mark_as_read(self, messages, unread=False):
        """Mark message(s) as read or unread.

        :returns: The json response from the server.

        """
        ids = []
        if isinstance(messages, Inboxable):
            ids.append(messages.fullname)
        elif hasattr(messages, '__iter__'):
            for msg in messages:
                if not isinstance(msg, Inboxable):
                    msg = 'Invalid message type: {0}'.format(type(msg))
                    raise ClientException(msg)
                ids.append(msg.fullname)
        else:
            msg = 'Invalid message type: {0}'.format(type(messages))
            raise ClientException(msg)
        # pylint: disable=W0212
        retval = self.reddit_session._mark_as_read(ids, unread=unread)
        # pylint: enable=W0212
        return retval

    def unfriend(self):
        """Unfriend the user.

        :returns: The json response from the server.

        """
        return self.friend(_unfriend=True)


class LoggedInRedditor(Redditor):
    """A class representing a currently logged in Redditor."""

    get_hidden = restrict_access('history')(_get_redditor_listing('hidden'))
    get_saved = restrict_access('history')(_get_redditor_listing('saved'))

    def get_blocked(self):
        """Return a UserList of Redditors with whom the user has blocked."""
        url = self.reddit_session.config['blocked']
        return self.reddit_session.request_json(url)

    def get_cached_moderated_reddits(self):
        """Return a cached dictionary of the user's moderated reddits.

        This list is used internally. Consider using the `get_my_moderation`
        function instead.

        """
        if self._mod_subs is None:
            self._mod_subs = {'mod': self.reddit_session.get_subreddit('mod')}
            for sub in self.reddit_session.get_my_moderation(limit=None):
                self._mod_subs[six.text_type(sub).lower()] = sub
        return self._mod_subs

    @deprecated('``get_friends`` has been moved to '
                ':class:`praw.AuthenticatedReddit` and will be removed from '
                ':class:`objects.LoggedInRedditor` in PRAW v4.0.0')
    def get_friends(self, **params):
        """Return a UserList of Redditors with whom the user is friends.

        This method has been moved to :class:`praw.AuthenticatedReddit`.

        """
        return self.reddit_session.get_friends(**params)


class ModAction(RedditContentObject):
    """A moderator action."""

    def __init__(self, reddit_session, json_dict=None, fetch=False):
        """Construct an instance of the ModAction object."""
        super(ModAction, self).__init__(reddit_session, json_dict, fetch)

    def __unicode__(self):
        """Return a string reprsentation of the moderator action."""
        return 'Action: {0}'.format(self.action)


class Submission(Editable, Gildable, Hideable, Moderatable, Refreshable,
                 Reportable, Saveable, Voteable):
    """A class for submissions to reddit."""

    _methods = (('select_flair', AR),)

    @staticmethod
    def _extract_more_comments(tree):
        """Return a list of MoreComments objects removed from tree."""
        more_comments = []
        queue = [(None, x) for x in tree]
        while len(queue) > 0:
            parent, comm = queue.pop(0)
            if isinstance(comm, MoreComments):
                heappush(more_comments, comm)
                if parent:
                    parent.replies.remove(comm)
                else:
                    tree.remove(comm)
            else:
                for item in comm.replies:
                    queue.append((comm, item))
        return more_comments

    @staticmethod
    def from_id(reddit_session, subreddit_id):
        """Return an edit-only submission object based on the id."""
        pseudo_data = {'id': subreddit_id,
                       'permalink': '/comments/{0}'.format(subreddit_id)}
        return Submission(reddit_session, pseudo_data)

    @staticmethod
    def from_json(json_response):
        """Return a submission object from the json response."""
        submission = json_response[0]['data']['children'][0]
        submission.comments = json_response[1]['data']['children']
        return submission

    @staticmethod
    @restrict_access(scope='read')
    def from_url(reddit_session, url, comment_limit=0, comment_sort=None,
                 comments_only=False, params=None):
        """Request the url and return a Submission object.

        :param reddit_session: The session to make the request with.
        :param url: The url to build the Submission object from.
        :param comment_limit: The desired number of comments to fetch. If <= 0
            fetch the default number for the session's user. If None, fetch the
            maximum possible.
        :param comment_sort: The sort order for retrieved comments. When None
            use the default for the session's user.
        :param comments_only: Return only the list of comments.
        :param params: dictionary containing extra GET data to put in the url.

        """
        if params is None:
            params = {}

        parsed = urlparse(url)
        query_pairs = parse_qs(parsed.query)
        get_params = dict((k, ",".join(v)) for k, v in query_pairs.items())
        params.update(get_params)
        url = urlunparse(parsed[:3] + ("", "", ""))
        if comment_limit is None:  # Fetch MAX
            params['limit'] = 2048  # Just use a big number
        elif comment_limit > 0:  # Use value
            params['limit'] = comment_limit
        if comment_sort:
            params['sort'] = comment_sort

        response = reddit_session.request_json(url, params=params)
        if comments_only:
            return response[1]['data']['children']
        submission = Submission.from_json(response)
        submission._comment_sort = comment_sort  # pylint: disable=W0212
        submission._params = params  # pylint: disable=W0212
        return submission

    def __init__(self, reddit_session, json_dict):
        """Construct an instance of the Subreddit object."""
        super(Submission, self).__init__(reddit_session, json_dict)
        # pylint: disable=E0203
        self._api_link = urljoin(reddit_session.config.api_url, self.permalink)
        # pylint: enable=E0203
        self.permalink = urljoin(reddit_session.config.permalink_url,
                                 self.permalink)
        self._comment_sort = None
        self._comments_by_id = {}
        self._comments = None
        self._orphaned = {}
        self._replaced_more = False
        self._params = {}

    @limit_chars
    def __unicode__(self):
        """Return a string representation of the Subreddit.

        Note: The representation is truncated to a fix number of characters.
        """
        title = self.title.replace('\r\n', ' ')
        return six.text_type('{0} :: {1}').format(self.score, title)

    def _insert_comment(self, comment):
        if comment.name in self._comments_by_id:  # Skip existing comments
            return

        comment._update_submission(self)  # pylint: disable=W0212

        if comment.name in self._orphaned:  # Reunite children with parent
            comment.replies.extend(self._orphaned[comment.name])
            del self._orphaned[comment.name]

        if comment.is_root:
            self._comments.append(comment)
        elif comment.parent_id in self._comments_by_id:
            self._comments_by_id[comment.parent_id].replies.append(comment)
        else:  # Orphan
            if comment.parent_id in self._orphaned:
                self._orphaned[comment.parent_id].append(comment)
            else:
                self._orphaned[comment.parent_id] = [comment]

    def _update_comments(self, comments):
        self._comments = comments
        for comment in self._comments:
            comment._update_submission(self)  # pylint: disable=W0212

    def add_comment(self, text):
        """Comment on the submission using the specified text.

        :returns: A Comment object for the newly created comment.

        """
        # pylint: disable=W0212
        response = self.reddit_session._add_comment(self.fullname, text)
        # pylint: enable=W0212
        self.reddit_session.evict(self._api_link)  # pylint: disable=W0212
        return response

    @property
    def comments(self):  # pylint: disable=E0202
        """Return forest of comments, with top-level comments as tree roots.

        May contain instances of MoreComment objects. To easily replace these
        objects with Comment objects, use the replace_more_comments method then
        fetch this attribute. Use comment replies to walk down the tree. To get
        an unnested, flat list of comments from this attribute use
        helpers.flatten_tree.

        """
        if self._comments is None:
            self.comments = Submission.from_url(  # pylint: disable=W0212
                self.reddit_session, self._api_link, comments_only=True)
        return self._comments

    @comments.setter  # NOQA
    def comments(self, new_comments):  # pylint: disable=E0202
        """Update the list of comments with the provided nested list."""
        self._update_comments(new_comments)
        self._orphaned = {}

    def get_duplicates(self, *args, **kwargs):
        """Return a get_content generator for the submission's duplicates.

        :returns: get_content generator iterating over Submission objects.

        The additional parameters are passed directly into
        :meth:`.get_content`. Note: the `url` and `object_filter` parameters
        cannot be altered.

        """
        url = self.reddit_session.config['duplicates'].format(
            submissionid=self.id)
        return self.reddit_session.get_content(url, *args, object_filter=1,
                                               **kwargs)

    def get_flair_choices(self, *args, **kwargs):
        """Return available link flair choices and current flair.

        Convenience function for
        :meth:`~.AuthenticatedReddit.get_flair_choices` populating both the
        `subreddit` and `link` parameters.

        :returns: The json response from the server.

        """
        return self.subreddit.get_flair_choices(self.fullname, *args, **kwargs)

    @restrict_access(scope='modposts')
    def lock(self):
        """Lock thread.

        Requires that the currently authenticated user has the modposts oauth
        scope or has user/password authentication as a mod of the subreddit.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['lock']
        data = {'id': self.fullname}
        return self.reddit_session.request_json(url, data=data)

    def mark_as_nsfw(self, unmark_nsfw=False):
        """Mark as Not Safe For Work.

        Requires that the currently authenticated user is the author of the
        submission, has the modposts oauth scope or has user/password
        authentication as a mod of the subreddit.

        :returns: The json response from the server.

        """
        def mark_as_nsfw_helper(self):  # pylint: disable=W0613
            # It is necessary to have the 'self' argument as it's needed in
            # restrict_access to determine what class the decorator is
            # operating on.
            url = self.reddit_session.config['unmarknsfw' if unmark_nsfw else
                                             'marknsfw']
            data = {'id': self.fullname}
            return self.reddit_session.request_json(url, data=data)

        is_author = (self.reddit_session.is_logged_in() and self.author ==
                     self.reddit_session.user)
        if is_author:
            return mark_as_nsfw_helper(self)
        else:
            return restrict_access('modposts')(mark_as_nsfw_helper)(self)

    def replace_more_comments(self, limit=32, threshold=1):
        """Update the comment tree by replacing instances of MoreComments.

        :param limit: The maximum number of MoreComments objects to
            replace. Each replacement requires 1 API request. Set to None to
            have no limit, or to 0 to make no extra requests. Default: 32
        :param threshold: The minimum number of children comments a
            MoreComments object must have in order to be replaced. Default: 1
        :returns: A list of MoreComments objects that were not replaced.

        Note that after making this call, the `comments` attribute of the
        submission will no longer contain any MoreComments objects. Items that
        weren't replaced are still removed from the tree, and will be included
        in the returned list.

        """
        if self._replaced_more:
            return []

        remaining = limit
        more_comments = self._extract_more_comments(self.comments)
        skipped = []

        # Fetch largest more_comments until reaching the limit or the threshold
        while more_comments:
            item = heappop(more_comments)
            if remaining == 0:  # We're not going to replace any more
                heappush(more_comments, item)  # It wasn't replaced
                break
            elif len(item.children) == 0 or 0 < item.count < threshold:
                heappush(skipped, item)  # It wasn't replaced
                continue

            # Fetch new comments and decrease remaining if a request was made
            new_comments = item.comments(update=False)
            if new_comments is not None and remaining is not None:
                remaining -= 1
            elif new_comments is None:
                continue

            # Re-add new MoreComment objects to the heap of more_comments
            for more in self._extract_more_comments(new_comments):
                more._update_submission(self)  # pylint: disable=W0212
                heappush(more_comments, more)
            # Insert the new comments into the tree
            for comment in new_comments:
                self._insert_comment(comment)

        self._replaced_more = True
        return more_comments + skipped

    def set_flair(self, *args, **kwargs):
        """Set flair for this submission.

        Convenience function that utilizes :meth:`.ModFlairMixin.set_flair`
        populating both the `subreddit` and `item` parameters.

        :returns: The json response from the server.

        """
        return self.subreddit.set_flair(self, *args, **kwargs)

    @restrict_access(scope='modposts')
    def set_contest_mode(self, state=True):
        """Set 'Contest Mode' for the comments of this submission.

        Contest mode have the following effects:
          * The comment thread will default to being sorted randomly.
          * Replies to top-level comments will be hidden behind
            "[show replies]" buttons.
          * Scores will be hidden from non-moderators.
          * Scores accessed through the API (mobile apps, bots) will be
            obscured to "1" for non-moderators.

        Source for effects: https://www.reddit.com/159bww/

        :returns: The json response from the server.

        """
        # TODO: Whether a submission is in contest mode is not exposed via the
        # API. Adding a test of this method is thus currently impossible.
        # Add a test when it becomes possible.
        url = self.reddit_session.config['contest_mode']
        data = {'id': self.fullname, 'state': state}
        return self.reddit_session.request_json(url, data=data)

    @restrict_access(scope='modposts')
    def set_suggested_sort(self, sort='blank'):
        """Set 'Suggested Sort' for the comments of the submission.

        Comments can be sorted in one of (confidence, top, new, hot,
        controversial, old, random, qa, blank).

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['suggested_sort']
        data = {'id': self.fullname, 'sort': sort}
        return self.reddit_session.request_json(url, data=data)

    @property
    def short_link(self):
        """Return a short link to the submission.

        The short link points to a page on the short_domain that redirects to
        the main. For example http://redd.it/eorhm is a short link for
        https://www.reddit.com/r/announcements/comments/eorhm/reddit_30_less_typing/.

        """
        return urljoin(self.reddit_session.config.short_domain, self.id)

    @restrict_access(scope='modposts')
    def sticky(self, bottom=True):
        """Sticky a post in its subreddit.

        If there is already a stickied post in the designated slot it will be
        unstickied.

        :param bottom: Set this as the top or bottom sticky. If no top sticky
            exists, this submission will become the top sticky regardless.

        :returns: The json response from the server

        """
        url = self.reddit_session.config['sticky_submission']
        data = {'id': self.fullname, 'state': True}
        if not bottom:
            data['num'] = 1
        return self.reddit_session.request_json(url, data=data)

    @restrict_access(scope='modposts')
    def unlock(self):
        """Lock thread.

        Requires that the currently authenticated user has the modposts oauth
        scope or has user/password authentication as a mod of the subreddit.

        :returns: The json response from the server.

        """
        url = self.reddit_session.config['unlock']
        data = {'id': self.fullname}
        return self.reddit_session.request_json(url, data=data)

    def unmark_as_nsfw(self):
        """Mark as Safe For Work.

        :returns: The json response from the server.

        """
        return self.mark_as_nsfw(unmark_nsfw=True)

    @restrict_access(scope='modposts')
    def unset_contest_mode(self):
        """Unset 'Contest Mode' for the comments of this submission.

        Contest mode have the following effects:
          * The comment thread will default to being sorted randomly.
          * Replies to top-level comments will be hidden behind
            "[show replies]" buttons.
          * Scores will be hidden from non-moderators.
          * Scores accessed through the API (mobile apps, bots) will be
            obscured to "1" for non-moderators.

        Source for effects: http://www.reddit.com/159bww/

        :returns: The json response from the server.

        """
        return self.set_contest_mode(False)

    @restrict_access(scope='modposts')
    def unsticky(self):
        """Unsticky this post.

        :returns: The json response from the server

        """
        url = self.reddit_session.config['sticky_submission']
        data = {'id': self.fullname, 'state': False}
        return self.reddit_session.request_json(url, data=data)


class Subreddit(Messageable, Refreshable):
    """A class for Subreddits."""

    _methods = (('accept_moderator_invite', AR),
                ('add_flair_template', MFMix),
                ('clear_flair_templates', MFMix),
                ('configure_flair', MFMix),
                ('delete_flair', MFMix),
                ('delete_image', MCMix),
                ('edit_wiki_page', AR),
                ('get_banned', MOMix),
                ('get_comments', UR),
                ('get_contributors', MOMix),
                ('get_edited', MOMix),
                ('get_flair', UR),
                ('get_flair_choices', AR),
                ('get_flair_list', MFMix),
                ('get_moderators', UR),
                ('get_mod_log', MLMix),
                ('get_mod_queue', MOMix),
                ('get_mod_mail', MOMix),
                ('get_muted', MOMix),
                ('get_random_submission', UR),
                ('get_reports', MOMix),
                ('get_rules', UR),
                ('get_settings', MCMix),
                ('get_spam', MOMix),
                ('get_sticky', UR),
                ('get_stylesheet', MOMix),
                ('get_traffic', UR),
                ('get_unmoderated', MOMix),
                ('get_wiki_banned', MOMix),
                ('get_wiki_contributors', MOMix),
                ('get_wiki_page', UR),
                ('get_wiki_pages', UR),
                ('leave_contributor', MSMix),
                ('leave_moderator', MSMix),
                ('search', UR),
                ('select_flair', AR),
                ('set_flair', MFMix),
                ('set_flair_csv', MFMix),
                ('set_settings', MCMix),
                ('set_stylesheet', MCMix),
                ('submit', SubmitMixin),
                ('subscribe', SubscribeMixin),
                ('unsubscribe', SubscribeMixin),
                ('update_settings', MCMix),
                ('upload_image', MCMix))

    # Subreddit banned
    add_ban = _modify_relationship('banned', is_sub=True)
    remove_ban = _modify_relationship('banned', unlink=True, is_sub=True)

    # Subreddit contributors
    add_contributor = _modify_relationship('contributor', is_sub=True)
    remove_contributor = _modify_relationship('contributor', unlink=True,
                                              is_sub=True)
    # Subreddit moderators
    add_moderator = _modify_relationship('moderator', is_sub=True)
    remove_moderator = _modify_relationship('moderator', unlink=True,
                                            is_sub=True)
    # Subreddit muted
    add_mute = _modify_relationship('muted', is_sub=True)
    remove_mute = _modify_relationship('muted', is_sub=True, unlink=True)

    # Subreddit wiki banned
    add_wiki_ban = _modify_relationship('wikibanned', is_sub=True)
    remove_wiki_ban = _modify_relationship('wikibanned', unlink=True,
                                           is_sub=True)
    # Subreddit wiki contributors
    add_wiki_contributor = _modify_relationship('wikicontributor', is_sub=True)
    remove_wiki_contributor = _modify_relationship('wikicontributor',
                                                   unlink=True, is_sub=True)

    # Generic listing selectors
    get_controversial = _get_sorter('controversial')
    get_hot = _get_sorter('')
    get_new = _get_sorter('new')
    get_top = _get_sorter('top')

    # Explicit listing selectors
    get_controversial_from_all = _get_sorter('controversial', t='all')
    get_controversial_from_day = _get_sorter('controversial', t='day')
    get_controversial_from_hour = _get_sorter('controversial', t='hour')
    get_controversial_from_month = _get_sorter('controversial', t='month')
    get_controversial_from_week = _get_sorter('controversial', t='week')
    get_controversial_from_year = _get_sorter('controversial', t='year')
    get_rising = _get_sorter('rising')
    get_top_from_all = _get_sorter('top', t='all')
    get_top_from_day = _get_sorter('top', t='day')
    get_top_from_hour = _get_sorter('top', t='hour')
    get_top_from_month = _get_sorter('top', t='month')
    get_top_from_week = _get_sorter('top', t='week')
    get_top_from_year = _get_sorter('top', t='year')

    def __init__(self, reddit_session, subreddit_name=None, json_dict=None,
                 fetch=False, **kwargs):
        """Construct an instance of the Subreddit object."""
        # Special case for when my_subreddits is called as no name is returned
        # so we have to extract the name from the URL. The URLs are returned
        # as: /r/reddit_name/
        if subreddit_name is None:
            subreddit_name = json_dict['url'].split('/')[2]

        if not isinstance(subreddit_name, six.string_types) \
                or not subreddit_name:
            raise TypeError('subreddit_name must be a non-empty string.')

        if fetch and ('+' in subreddit_name or '-' in subreddit_name):
            fetch = False
            warn_explicit('fetch=True has no effect on multireddits',
                          UserWarning, '', 0)

        info_url = reddit_session.config['subreddit_about'].format(
            subreddit=subreddit_name)
        self._case_name = subreddit_name
        super(Subreddit, self).__init__(reddit_session, json_dict, fetch,
                                        info_url, **kwargs)
        self.display_name = self._case_name
        self._url = reddit_session.config['subreddit'].format(
            subreddit=self.display_name)
        # '' is the hot listing
        listings = ['new/', '', 'top/', 'controversial/', 'rising/']
        base = reddit_session.config['subreddit'].format(
            subreddit=self.display_name)
        self._listing_urls = [base + x + '.json' for x in listings]

    def __repr__(self):
        """Return a code representation of the Subreddit."""
        return 'Subreddit(subreddit_name=\'{0}\')'.format(self.display_name)

    def __unicode__(self):
        """Return a string representation of the Subreddit."""
        return self.display_name

    def _post_populate(self, fetch):
        if fetch:
            # Maintain a consistent `display_name` until the user
            # explicitly calls `subreddit.refresh()`
            tmp = self._case_name
            self._case_name = self.display_name
            self.display_name = tmp

    def clear_all_flair(self):
        """Remove all user flair on this subreddit.

        :returns: The json response from the server when there is flair to
            clear, otherwise returns None.

        """
        csv = [{'user': x['user']} for x in self.get_flair_list(limit=None)]
        if csv:
            return self.set_flair_csv(csv)
        else:
            return


class Multireddit(Refreshable):
    """A class for users' Multireddits."""

    # Generic listing selectors
    get_controversial = _get_sorter('controversial')
    get_hot = _get_sorter('')
    get_new = _get_sorter('new')
    get_top = _get_sorter('top')

    # Explicit listing selectors
    get_controversial_from_all = _get_sorter('controversial', t='all')
    get_controversial_from_day = _get_sorter('controversial', t='day')
    get_controversial_from_hour = _get_sorter('controversial', t='hour')
    get_controversial_from_month = _get_sorter('controversial', t='month')
    get_controversial_from_week = _get_sorter('controversial', t='week')
    get_controversial_from_year = _get_sorter('controversial', t='year')
    get_rising = _get_sorter('rising')
    get_top_from_all = _get_sorter('top', t='all')
    get_top_from_day = _get_sorter('top', t='day')
    get_top_from_hour = _get_sorter('top', t='hour')
    get_top_from_month = _get_sorter('top', t='month')
    get_top_from_week = _get_sorter('top', t='week')
    get_top_from_year = _get_sorter('top', t='year')

    @classmethod
    def from_api_response(cls, reddit_session, json_dict):
        """Return an instance of the appropriate class from the json dict."""
        # The Multireddit response contains the Subreddits attribute as a list
        # of dicts of the form {'name': 'subredditname'}.
        # We must convert each of these into a Subreddit object.
        json_dict['subreddits'] = [Subreddit(reddit_session, item['name'])
                                   for item in json_dict['subreddits']]
        return cls(reddit_session, None, None, json_dict)

    def __init__(self, reddit_session, author=None, name=None,
                 json_dict=None, fetch=False, **kwargs):
        """Construct an instance of the Multireddit object."""
        author = six.text_type(author) if author \
            else json_dict['path'].split('/')[-3]
        if not name:
            name = json_dict['path'].split('/')[-1]

        info_url = reddit_session.config['multireddit_about'].format(
            user=author, multi=name)
        self.name = name
        self._author = author
        super(Multireddit, self).__init__(reddit_session, json_dict, fetch,
                                          info_url, **kwargs)
        self._url = reddit_session.config['multireddit'].format(
            user=author, multi=name)

    def __repr__(self):
        """Return a code representation of the Multireddit."""
        return 'Multireddit(author=\'{0}\', name=\'{1}\')'.format(
            self._author, self.name)

    def __unicode__(self):
        """Return a string representation of the Multireddit."""
        return self.name

    def _post_populate(self, fetch):
        if fetch:
            # Subreddits are returned as dictionaries in the form
            # {'name': 'subredditname'}. Convert them to Subreddit objects.
            self.subreddits = [Subreddit(self.reddit_session, item['name'])
                               for item in self.subreddits]

            # paths are of the form "/user/{USERNAME}/m/{MULTINAME}"
            author = self.path.split('/')[2]
            self.author = Redditor(self.reddit_session, author)

    @restrict_access(scope='subscribe')
    def add_subreddit(self, subreddit, _delete=False, *args, **kwargs):
        """Add a subreddit to the multireddit.

        :param subreddit: The subreddit name or Subreddit object to add

        The additional parameters are passed directly into
        :meth:`~praw.__init__.BaseReddit.request_json`.

        """
        subreddit = six.text_type(subreddit)
        url = self.reddit_session.config['multireddit_add'].format(
            user=self._author, multi=self.name, subreddit=subreddit)
        method = 'DELETE' if _delete else 'PUT'
        self.reddit_session.http.headers['x-modhash'] = \
            self.reddit_session.modhash
        data = {'model': dumps({'name': subreddit})}
        try:
            self.reddit_session.request(url, data=data, method=method,
                                        *args, **kwargs)
        finally:
            del self.reddit_session.http.headers['x-modhash']

    @restrict_access(scope='subscribe')
    def copy(self, to_name):
        """Copy this multireddit.

        Convenience function that utilizes
        :meth:`.MultiredditMixin.copy_multireddit` populating both
        the `from_redditor` and `from_name` parameters.

        """
        return self.reddit_session.copy_multireddit(self._author, self.name,
                                                    to_name)

    @restrict_access(scope='subscribe')
    def delete(self):
        """Delete this multireddit.

        Convenience function that utilizes
        :meth:`.MultiredditMixin.delete_multireddit` populating the `name`
        parameter.

        """
        return self.reddit_session.delete_multireddit(self.name)

    @restrict_access(scope='subscribe')
    def edit(self, *args, **kwargs):
        """Edit this multireddit.

        Convenience function that utilizes
        :meth:`.MultiredditMixin.edit_multireddit` populating the `name`
        parameter.

        """
        return self.reddit_session.edit_multireddit(name=self.name, *args,
                                                    **kwargs)

    @restrict_access(scope='subscribe')
    def remove_subreddit(self, subreddit, *args, **kwargs):
        """Remove a subreddit from the user's multireddit."""
        return self.add_subreddit(subreddit, True, *args, **kwargs)

    @restrict_access(scope='subscribe')
    def rename(self, new_name, *args, **kwargs):
        """Rename this multireddit.

        This function is a handy shortcut to
        :meth:`rename_multireddit` of the reddit_session.

        """
        new = self.reddit_session.rename_multireddit(self.name, new_name,
                                                     *args, **kwargs)
        self.__dict__ = new.__dict__  # pylint: disable=W0201
        return self


class PRAWListing(RedditContentObject):
    """An abstract class to coerce a listing into RedditContentObjects."""

    CHILD_ATTRIBUTE = None

    def __init__(self, reddit_session, json_dict=None, fetch=False):
        """Construct an instance of the PRAWListing object."""
        super(PRAWListing, self).__init__(reddit_session, json_dict, fetch)

        if not self.CHILD_ATTRIBUTE:
            raise NotImplementedError('PRAWListing must be extended.')

        child_list = getattr(self, self.CHILD_ATTRIBUTE)
        for i in range(len(child_list)):
            child_list[i] = self._convert(reddit_session, child_list[i])

    def __contains__(self, item):
        """Test if item exists in the listing."""
        return item in getattr(self, self.CHILD_ATTRIBUTE)

    def __delitem__(self, index):
        """Remove the item at position index from the listing."""
        del getattr(self, self.CHILD_ATTRIBUTE)[index]

    def __getitem__(self, index):
        """Return the item at position index in the listing."""
        return getattr(self, self.CHILD_ATTRIBUTE)[index]

    def __iter__(self):
        """Return an iterator to the listing."""
        return getattr(self, self.CHILD_ATTRIBUTE).__iter__()

    def __len__(self):
        """Return the number of items in the listing."""
        return len(getattr(self, self.CHILD_ATTRIBUTE))

    def __setitem__(self, index, item):
        """Set item at position `index` in the listing."""
        getattr(self, self.CHILD_ATTRIBUTE)[index] = item

    def __unicode__(self):
        """Return a string representation of the listing."""
        return six.text_type(getattr(self, self.CHILD_ATTRIBUTE))


class UserList(PRAWListing):
    """A list of Redditors. Works just like a regular list."""

    CHILD_ATTRIBUTE = 'children'

    @staticmethod
    def _convert(reddit_session, data):
        """Return a Redditor object from the data."""
        retval = Redditor(reddit_session, data['name'], fetch=False)
        retval.id = data['id'].split('_')[1]  # pylint: disable=C0103,W0201
        return retval


class WikiPage(Refreshable):
    """An individual WikiPage object."""

    @classmethod
    def from_api_response(cls, reddit_session, json_dict):
        """Return an instance of the appropriate class from the json_dict."""
        # The WikiPage response does not contain the necessary information
        # in the JSON response to determine the name of the page nor the
        # subreddit it belongs to. Thus we must extract this information
        # from the request URL.
        # pylint: disable=W0212
        parts = reddit_session._request_url.split('/', 6)
        # pylint: enable=W0212
        subreddit = parts[4]
        page = parts[6].split('.', 1)[0]
        return cls(reddit_session, subreddit, page, json_dict=json_dict)

    def __init__(self, reddit_session, subreddit=None, page=None,
                 json_dict=None, fetch=False, **kwargs):
        """Construct an instance of the WikiPage object."""
        if not subreddit and not page:
            subreddit = json_dict['sr']
            page = json_dict['page']
        info_url = reddit_session.config['wiki_page'].format(
            subreddit=six.text_type(subreddit), page=page)
        super(WikiPage, self).__init__(reddit_session, json_dict, fetch,
                                       info_url, **kwargs)
        self.page = page
        self.subreddit = subreddit

    def __unicode__(self):
        """Return a string representation of the page."""
        return six.text_type('{0}:{1}').format(self.subreddit, self.page)

    @restrict_access(scope='modwiki')
    def add_editor(self, username, _delete=False, *args, **kwargs):
        """Add an editor to this wiki page.

        :param username: The name or Redditor object of the user to add.
        :param _delete: If True, remove the user as an editor instead.
            Please use :meth:`remove_editor` rather than setting it manually.

        Additional parameters are passed into
        :meth:`~praw.__init__.BaseReddit.request_json`.
        """
        url = self.reddit_session.config['wiki_page_editor']
        url = url.format(subreddit=six.text_type(self.subreddit),
                         method='del' if _delete else 'add')

        data = {'page': self.page,
                'username': six.text_type(username)}
        return self.reddit_session.request_json(url, data=data, *args,
                                                **kwargs)

    @restrict_access(scope='modwiki')
    def get_settings(self, *args, **kwargs):
        """Return the settings for this wiki page.

        Includes permission level, names of editors, and whether
        the page is listed on /wiki/pages.

        Additional parameters are passed into
        :meth:`~praw.__init__.BaseReddit.request_json`
        """
        url = self.reddit_session.config['wiki_page_settings']
        url = url.format(subreddit=six.text_type(self.subreddit),
                         page=self.page)
        return self.reddit_session.request_json(url, *args, **kwargs)['data']

    def edit(self, *args, **kwargs):
        """Edit the wiki page.

        Convenience function that utilizes
        :meth:`.AuthenticatedReddit.edit_wiki_page` populating both the
        ``subreddit`` and ``page`` parameters.
        """
        return self.subreddit.edit_wiki_page(self.page, *args, **kwargs)

    @restrict_access(scope='modwiki')
    def edit_settings(self, permlevel, listed, *args, **kwargs):
        """Edit the settings for this individual wiki page.

        :param permlevel: Who can edit this page?
            (0) use subreddit wiki permissions, (1) only approved wiki
            contributors for this page may edit (see
            :meth:`~praw.objects.WikiPage.add_editor`), (2) only mods may edit
            and view
        :param listed: Show this page on the listing?
            True - Appear in /wiki/pages
            False - Do not appear in /wiki/pages
        :returns: The updated settings data.

        Additional parameters are passed into :meth:`request_json`.

        """
        url = self.reddit_session.config['wiki_page_settings']
        url = url.format(subreddit=six.text_type(self.subreddit),
                         page=self.page)
        data = {'permlevel': permlevel,
                'listed': 'on' if listed else 'off'}

        return self.reddit_session.request_json(url, data=data, *args,
                                                **kwargs)['data']

    def remove_editor(self, username, *args, **kwargs):
        """Remove an editor from this wiki page.

        :param username: The name or Redditor object of the user to remove.

        This method points to :meth:`add_editor` with _delete=True.

        Additional parameters are are passed to :meth:`add_editor` and
        subsequently into :meth:`~praw.__init__.BaseReddit.request_json`.
        """
        return self.add_editor(username=username, _delete=True, *args,
                               **kwargs)


class WikiPageListing(PRAWListing):
    """A list of WikiPages. Works just like a regular list."""

    CHILD_ATTRIBUTE = '_tmp'

    @staticmethod
    def _convert(reddit_session, data):
        """Return a WikiPage object from the data."""
        # TODO: The _request_url hack shouldn't be necessary
        # pylint: disable=W0212
        subreddit = reddit_session._request_url.rsplit('/', 4)[1]
        # pylint: enable=W0212
        return WikiPage(reddit_session, subreddit, data, fetch=False)


def _add_aliases():
    def predicate(obj):
        return inspect.isclass(obj) and hasattr(obj, '_methods')

    import inspect
    import sys

    for _, cls in inspect.getmembers(sys.modules[__name__], predicate):
        for name, mixin in cls._methods:  # pylint: disable=W0212
            setattr(cls, name, alias_function(getattr(mixin, name),
                                              mixin.__name__))
_add_aliases()

import re
import six
from .page import Page
from .subreddit import SubredditPage
from .submission import SubmissionPage
from .subscription import SubscriptionPage

class UnknownBinding(Exception):
    pass


class NonStandardKey(Exception):
    pass


class KeyMap(dict):

    default_bindings = {
        'main-exit': 'q',
        'main-force_exit': 'Q',
        'main-show_help': '?',
        'main-sort_content_hot': '1',
        'main-sort_content_top': '2',
        'main-sort_content_rising': '3',
        'main-sort_content_new': '4',
        'main-sort_content_controversial': '5',
        'main-move_cursor_up': 's',
        'main-move_cursor_down': 't',
        'main-move_page_up': 'm',
        'main-move_page_down': 'n',
        'main-upvote': 'a',
        'main-downvote': 'z',
        'main-login': 'u',
        'main-delete_item': 'd',
        'main-edit': 'e',
        'main-get_inbox': 'i',

        'submission-toggle_comment': 'l',
        'submission-exit_submission': 'h',
        'submission-refresh_content': 'r',
        'submission-open_link': 'o',
        'submission-add_comment': 'c',
        'submission-delete_comment': 'd',

        'subreddit-refresh_content': 'r',
        'subreddit-search_subreddit': 'f',
        'subreddit-prompt_subreddit': '/',
        'subreddit-open_submission': 'l',
        'subreddit-open_link': 'o',
        'subreddit-post_submission': 'c',
        'subreddit-open_subscriptions': 's',

        'subscription-refresh_content': 'r',
        'subscription-select_subreddit': 'l',
        'subscription-close_subscriptions': 'h'
    }

    userPageMap = {}
    userSubredditMap = {}
    userSubscriptionMap = {}
    userSubmissionMap = {}

    def __init__(self, userMap=None):
        super(KeyMap, self).__init__()

        if userMap:
            self.loadUserMap(userMap)

    def __setitem__(self, binding, key):
        self.bind(binding, key)

    def loadUserMap(self, userMap):
        for bind in userMap:
            key = userMap[bind]
            try:
                self.bind(bind, key)
            except UnknownBinding:
                print("binding "+bind+" Don't exist")
            except NonStandardKey:
                print("key \""+key+"\" is not standart")

    def addUserBinding(self, key, keymap, function):
        if key not in keymap:
            keymap[key] = function
        else:
            print(key+" is mapped multiple time")

    def bind(self, binding, key):

        if binding in self.default_bindings:
            keymap, function = self.binding2function(binding)
            if isinstance(key, six.string_types) and len(key) == 1:
                self.addUserBinding(ord(key), keymap, function)
            else:
                raise NonStandardKey()
        else:
            raise UnknownBinding()

    def binding2function(self, binding):
        """ Get the keymap and method reference of a binding's string """

        s = binding.split('-')

        if re.match('^main-', binding):
            return (self.userPageMap, eval('Page.'+s[1]))
        if re.match('^submission-', binding):
            return (self.userSubmissionMap, eval('SubmissionPage.'+s[1]))
        if re.match('^subreddit-', binding):
            return (self.userSubredditMap, eval('SubredditPage.'+s[1]))
        if re.match('^subscription-', binding):
            return (self.userSubscriptionMap, eval('SubscriptionPage.'+s[1]))

    def fillWithDefaultKey(self):
        for binding, key in self.default_bindings.items():
            keymap, function = self.binding2function(binding)
            if function not in keymap.values():
                print("Add default binding "+binding)
                keymap[ord(key[0])] = function

import re
import six
import curses

from .page import Page, PageController
from .subreddit import SubredditPage, SubredditController
from .submission import SubmissionPage, SubmissionController
from .subscription import SubscriptionPage, SubscriptionController
from .terminal import Terminal


class UnknownBinding(Exception):
    pass


class NonStandardKey(Exception):
    pass


class KeyMap(dict):

    default_bindings = {
        'main-exit': ['q'],
        'main-force_exit': ['Q'],
        'main-show_help': ['?'],
        'main-sort_content_hot': ['1'],
        'main-sort_content_top': ['2'],
        'main-sort_content_rising': ['3'],
        'main-sort_content_new': ['4'],
        'main-sort_content_controversial': ['5'],
        'main-move_cursor_up': ['k'],
        'main-move_cursor_down': ['j'],
        'main-move_page_up': ['m'],
        'main-move_page_down': ['n'],
        'main-upvote': ['a'],
        'main-downvote': ['z'],
        'main-login': ['u'],
        'main-delete_item': ['d'],
        'main-edit': ['e'],
        'main-get_inbox': ['i'],

        'submission-toggle_comment': ['l'],
        'submission-exit_submission': ['h'],
        'submission-refresh_content': ['r'],
        'submission-open_link': ['o', Terminal.RETURN],
        'submission-add_comment': ['c'],
        'submission-delete_comment': ['d'],

        'subreddit-refresh_content': ['r'],
        'subreddit-search_subreddit': ['f'],
        'subreddit-prompt_subreddit': ['/'],
        'subreddit-open_submission': ['l'],
        'subreddit-open_link': ['o'],
        'subreddit-post_submission': ['c'],
        'subreddit-open_subscriptions': ['s'],

        'subscription-refresh_content': ['r'],
        'subscription-select_subreddit': ['l', curses.KEY_ENTER],
        'subscription-close_subscriptions': ['h']
    }

    userPageMap = {}
    userSubredditMap = {}
    userSubscriptionMap = {}
    userSubmissionMap = {}

    def __init__(self, userMap=None):
        super(KeyMap, self).__init__()

        if userMap:
            self.loadUserMap(userMap)
        self.fillWithDefaultKey()
        self.fillController()

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
            print(chr(key)+" is mapped multiple time")

    def bind(self, binding, key):

        if binding in self.default_bindings:
            keymap = self.bindingKeyMap(binding)
            if isinstance(key, six.string_types) and len(key) == 1:
                self.addUserBinding(ord(key), keymap, binding)
            else:
                raise NonStandardKey()
        else:
            raise UnknownBinding()

    def bindingFunction(self, binding):
        base_class, function, controller, keymap = self.bindingInfo(binding)
        return function

    def bindingClass(self, binding):
        base_class, function, controller, keymap = self.bindingInfo(binding)
        return base_class

    def bindingController(self, binding):
        base_class, function, controller, keymap = self.bindingInfo(binding)
        return controller

    def bindingKeyMap(self, binding):
        base_class, function, controller, keymap = self.bindingInfo(binding)
        return keymap

    def bindingInfo(self, binding):
        base_class = None
        controller = None
        function = None
        keymap = None

        s = binding.split('-')

        if re.match('^main-', binding):
            base_class = Page
            keymap = self.userPageMap
            function = eval('Page.'+s[1])
            controller = PageController
        if re.match('^submission-', binding):
            base_class = SubmissionPage
            keymap = self.userSubmissionMap
            function = eval('SubmissionPage.'+s[1])
            controller = SubmissionController
        if re.match('^subreddit-', binding):
            base_class = SubredditPage
            keymap = self.userSubredditMap
            function = eval('SubredditPage.'+s[1])
            controller = SubredditController
        if re.match('^subscription-', binding):
            base_class = SubscriptionPage
            keymap = self.userSubscriptionMap
            function = eval('SubscriptionPage.'+s[1])
            controller = SubscriptionController

        return base_class, function, controller, keymap

    def fillWithDefaultKey(self):
        for binding, keys in self.default_bindings.items():
            keymap = self.bindingKeyMap(binding)
            if binding not in keymap.values():
                for key in keys:
                    if isinstance(key, six.text_type):
                        keymap[ord(key[0])] = binding
                    else:
                        keymap[key] = binding

    def emptyController(self):
        PageController.character_map = {}
        SubredditController.character_map = {}
        SubmissionController.character_map = {}
        SubscriptionController.character_map = {}

    def fillController(self):
        keymap = {}
        self.emptyController()

        for key, binding in self.userPageMap.items():
            base_class, function, controller, keymap = self.bindingInfo(binding)
            controller.bind(function, key)

        for key, binding in self.userSubredditMap.items():
            base_class, function, controller, keymap = self.bindingInfo(binding)
            controller.bind(function, key)

        for key, binding in self.userSubmissionMap.items():
            base_class, function, controller, keymap = self.bindingInfo(binding)
            controller.bind(function, key)

        for key, binding in self.userSubscriptionMap.items():
            base_class, function, controller, keymap = self.bindingInfo(binding)
            controller.bind(function, key)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class EscapeInterrupt(Exception):
    "Signal that the ESC key has been pressed"


class RTVError(Exception):
    "Base RTV error class"


class KeystringError(RTVError):
    "Unable to parse key string"


class ConfigError(RTVError):
    "There was a problem with the configuration"


class AccountError(RTVError):
    "Could not access user account"


class SubmissionError(RTVError):
    "Submission could not be loaded"


class SubredditError(RTVError):
    "Subreddit could not be reached"


class SubscriptionError(RTVError):
    "Subscriptions could not be fetched"


class ProgramError(RTVError):
    "Problem executing an external program"


class BrowserError(RTVError):
    "Could not open a web browser tab"
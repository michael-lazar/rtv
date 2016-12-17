# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class EscapeInterrupt(Exception):
    "Signal that the ESC key has been pressed"


class ConfigError(Exception):
    "There was a problem with the configuration"


class RTVError(Exception):
    "Base RTV error class"


class AccountError(RTVError):
    "Could not access user account"


class SubmissionError(RTVError):
    "Submission could not be loaded"


class NoSubmissionsError(RTVError):
    "No submissions for the given page"

    def __init__(self, name):
        self.name = name
        message = '`{0}` has no submissions'.format(name)
        super(NoSubmissionsError, self).__init__(message)


class SubscriptionError(RTVError):
    "Content could not be fetched"


class ProgramError(RTVError):
    "Problem executing an external program"


class BrowserError(RTVError):
    "Could not open a web browser tab"


class TemporaryFileError(RTVError):
    "Indicates that an error has occurred and the file should not be deleted"


class MailcapEntryNotFound(RTVError):
    "A valid mailcap entry could not be coerced from the given url"
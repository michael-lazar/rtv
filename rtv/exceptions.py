class EscapeInterrupt(Exception):
    "Signal that the ESC key has been pressed"


class RTVError(Exception):
    "Base RTV error class"


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

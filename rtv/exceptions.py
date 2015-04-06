class EscapeInterrupt(Exception):
    "Signal that the ESC key has been pressed"


class RTVError(Exception):
    "Base RTV error class"


class AccountError(RTVError):
    "Could not access user account"


class SubmissionError(RTVError):
    "Submission could not be loaded"

    def __init__(self, url):
        self.url = url


class SubredditError(RTVError):
    "Subreddit could not be reached"

    def __init__(self, name):
        self.name = name


class ProgramError(RTVError):
    "Problem executing an external program"

    def __init__(self, name):
        self.name = name

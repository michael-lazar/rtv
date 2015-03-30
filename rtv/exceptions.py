class SubmissionError(Exception):
    "Submission could not be loaded"
    def __init__(self, url):
        self.url = url

class SubredditError(Exception):
    "Subreddit could not be reached"
    def __init__(self, name):
        self.name = name

class ProgramError(Exception):
    "Problem executing an external program"
    def __init__(self, name):
        self.name = name

class EscapeInterrupt(Exception):
    "Signal that the ESC key has been pressed"
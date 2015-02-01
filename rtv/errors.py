class EscapePressed(Exception):
    pass

class SubmissionURLError(Exception):

    def __init__(self, url):
        self.url = url

class SubredditNameError(Exception):

    def __init__(self, name):
        self.name = name
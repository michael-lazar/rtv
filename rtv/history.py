import os


__all__ = ['load_history', 'save_history']


def history_path():
    """
    Create the path to the history log
    """
    HOME = os.path.expanduser('~')
    XDG_CONFIG_HOME = os.getenv('XDG_CACHE_HOME', os.path.join(HOME, '.config'))
    path = os.path.join(XDG_CONFIG_HOME, 'rtv')
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, 'history.log')


def load_history():
    """
    Load the history file into memory if it exists
    """
    path = history_path()
    if os.path.exists(path):
        with open(path) as history_file:
            # reverse the list so the newest ones are first
            history = [line.strip() for line in history_file][::-1]
            return OrderedSet(history)
    return OrderedSet()


def save_history(history):
    """
    Save the visited links to the history log
    """
    path = history_path()
    with open(path, 'w+') as history_file:
        for i in range(200):
            if not history:
                break
            try:
                history_file.write(history.pop() + '\n')
            except UnicodeEncodeError:
                # Ignore unicode URLS, may want to handle this at some point
                continue

class OrderedSet(object):
    """
    A simple implementation of an ordered set. A set is used to check
    for membership, and a list is used to maintain ordering.
    """

    def __init__(self, elements=[]):
        self._set = set(elements)
        self._list = elements

    def __contains__(self, item):
        return item in self._set

    def __len__(self):
        return len(self._list)

    def add(self, item):
        self._set.add(item)
        self._list.append(item)

    def pop(self):
        return self._list.pop()

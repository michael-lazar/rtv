import os


__all__ = ['load_history', 'save_history']


def history_path():
    """
    Create the path to the history log
    """
    HOME = os.path.expanduser('~')
    XDG_CONFIG_HOME = os.getenv('XDG_CACHE_HOME', os.path.join(HOME, '.config'))
    path = os.path.join(XDG_CONFIG_HOME, 'rtv', 'history.log')
    return path


def load_history():
    """
    Load the history file into memory if it exists
    """
    path = history_path()
    if os.path.exists(path):
        with open(path) as history_file:
            return set([line.replace('\n', '') for line in history_file])
    return set()


def save_history(history):
    """
    Save the visited links to the history log
    """
    path = history_path()
    with open(path, 'w+') as history_file:
        for i in range(200):
            if not history:
                break
            history_file.write(history.pop() + '\n')
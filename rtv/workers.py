import time
import sys
import os
import threading
import subprocess

def open_browser(url):
    """
    Call webbrowser.open_new_tab(url) and redirect stdout/stderr to devnull.

    This is a workaround to stop firefox from spewing warning messages to the
    console. See http://bugs.python.org/issue22277 for a better description
    of the problem.
    """
    command = "import webbrowser; webbrowser.open_new_tab('%s')" % url
    args = [sys.executable, '-c', command]
    with open(os.devnull, 'ab+', 0) as null:
        subprocess.check_call(args, stdout=null, stderr=null)


class LoadScreen(object):
    """
    Display a loading dialog while waiting for a blocking action to complete.

    This class spins off a seperate thread to animate the loading screen in the
    background.

    Usage:
        #>>> loader = LoadScreen(stdscr)
        #>>> with loader(...):
        #>>>     blocking_request(...)
    """

    def __init__(self, stdscr):

        self._stdscr = stdscr

        self._args = None
        self._animator = None
        self._is_running = None

    def __call__(
            self,
            delay=0.5,
            interval=0.4,
            message='Downloading',
            trail='...'):

        self._args = (delay, interval, message, trail)
        return self

    def __enter__(self):

        self._animator = threading.Thread(target=self.animate, args=self._args)
        self._animator.daemon = True

        self._is_running = True
        self._animator.start()

    def __exit__(self, exc_type, exc_val, exc_tb):

        self._is_running = False
        self._animator.join()

        # Check for timeout error

    def animate(self, delay, interval, message, trail):

        # Delay before starting animation to avoid wasting resources if the
        # wait time is very short
        start = time.time()
        while (time.time() - start) < delay:
            if not self._is_running:
                return

        message_len = len(message) + len(trail)
        n_rows, n_cols = self._stdscr.getmaxyx()
        s_row = (n_rows - 3) // 2
        s_col = (n_cols - message_len - 1) // 2
        window = self._stdscr.derwin(3, message_len+2, s_row, s_col)

        while True:
            for i in range(len(trail)+1):

                if not self._is_running:
                    window.clear()
                    window = None
                    self._stdscr.refresh()
                    return

                window.erase()
                window.border()
                window.addstr(1, 1, message + trail[:i])
                window.refresh()
                time.sleep(interval)
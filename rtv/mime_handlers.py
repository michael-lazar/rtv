"""Special handlers for displaying data with certain mimetypes."""

import base64
import os
import time

import requests


def iterm2_image_viewer(terminal, link):
    """Display an image inline with iTerm2 version 3+."""
    height, width = terminal.stdscr.getmaxyx()

    def encode_image(data):
        # This is based on the iTerm2 imgcat script:
        # https://raw.githubusercontent.com/gnachman/iTerm2/master/tests/imgcat
        is_tmux = os.getenv('TERM', '').startswith('screen')
        encoded_data = base64.b64encode(data)

        imgseq = [b'\033Ptmux;\033\033]' if is_tmux else b'\033]']
        imgseq.append(b'1337;File=')
        imgseq.append(b'width=' + str(width).encode())
        # Save some room for extra information at the bottom.
        imgseq.append(b';height=' + str(height - 2).encode())
        imgseq.append(b";preserveAspectRatio=true;inline=1:")
        imgseq.append(encoded_data)
        imgseq.append(b'\a\033\\' if is_tmux else b'\a')
        return b''.join(imgseq)

    with terminal.loader('Downloading image'):
        req = requests.get(link, stream=True)
        if req.status_code != 200:
            terminal.show_notification(
                'Failed to download image. Status code = %d' % req.status_code)
            return

        req.raw.decode_content = True
        image_data = encode_image(req.raw.read())

    # Create a new blank window that takes up the whole screen.
    win = terminal.stdscr.derwin(height, width, 0, 0)
    win.erase()
    win.refresh()
    # Curses doesn't seem to be able to handle this data for some reason.
    # Use print() to overlay on window.
    print(image_data.decode('utf-8'))
    # We resized the image to make sure there's room for this.
    win.addstr(height - 2, 0, 'url: %s' % link)
    win.addstr(height - 1, 0, 'press any key to continue...')
    terminal.stdscr.touchwin()
    terminal.stdscr.refresh()

    # Wait for a keypress.
    while True:
        if terminal.getch() != -1:
            break
        time.sleep(0.01)

    # Clear the whole screen again.
    win.clear()
    win.refresh()
    del win
    terminal.stdscr.touchwin()
    terminal.stdscr.refresh()

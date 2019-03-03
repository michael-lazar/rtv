#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scrape the project contributors list from Github and update AUTHORS.rst
"""

from __future__ import unicode_literals
import os
import time
import logging

import requests

_filepath = os.path.dirname(os.path.relpath(__file__))

FILENAME = os.path.abspath(os.path.join(_filepath, '..', 'AUTHORS.rst'))
URL = "https://api.github.com/repos/michael-lazar/rtv/contributors?per_page=1000"
HEADER = """\
================
RTV Contributors
================

Thanks to the following people for their contributions to this project.

"""


def main():

    logging.captureWarnings(True)

    # Request the list of contributors
    print('GET {}'.format(URL))
    resp = requests.get(URL)
    contributors = resp.json()

    lines = []
    for contributor in contributors:
        time.sleep(1.0)

        # Request each contributor individually to get the full name
        print('GET {}'.format(contributor['url']))
        resp = requests.get(contributor['url'])
        user = resp.json()

        name = user.get('name') or contributor['login']
        url = user['html_url']
        lines.append('* `{} <{}>`_'.format(name, url))

    print('Writing to {}'.format(FILENAME))
    text = HEADER + '\n'.join(lines)
    text = text.encode('utf-8')
    with open(FILENAME, 'wb') as fp:
        fp.write(text)


if __name__ == '__main__':
    main()

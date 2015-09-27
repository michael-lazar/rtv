"""
Internal tool used to automatically generate an up-to-date version of the rtv
man page. Currently this script should be manually ran after each version bump.
In the future, it would be nice to have this functionality built into setup.py.

Usage:
    $ python scripts/build_manpage.py
"""
from datetime import datetime

from rtv import docs, config

parser = config.build_parser()
help = parser.format_help()
help_sections = help.split('\n\n')

data = {}
data['version'] = docs.__version__
data['release_date'] = datetime.utcnow().strftime('%B %d, %Y')
data['synopsis'] = help_sections[0].replace('usage: ', '')
data['description'] = help_sections[1]

options = ''
arguments = help_sections[2].split('\n')[:1]
for argument in arguments:
    options += ''


pass

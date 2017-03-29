"""
This stub allows the end-user to fallback to their system installation of praw 
if the bundled package missing. This technique was inspired by the requests
library and how it handles dependencies.

Reference:
    https://github.com/kennethreitz/requests/blob/master/requests/packages/__init__.py
"""
from __future__ import absolute_import
import sys


__praw_hash__ = 'a632ff005fc09e74a8d3d276adc10aa92638962c'


try:
    from . import praw
except ImportError:
    import praw
    if not praw.__version__.startswith('3.'):
        msg = 'Invalid PRAW version {0}, exiting'.format(praw.__version__)
        raise RuntimeError(msg)
    sys.modules['%s.praw' % __name__] = praw

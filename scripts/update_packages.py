#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Update the project's bundled dependencies by downloading the git repository and
copying over the most recent commit.
"""

import os
import shutil
import subprocess
import tempfile

_filepath = os.path.dirname(os.path.relpath(__file__))
ROOT = os.path.abspath(os.path.join(_filepath, '..'))

PRAW_REPO = 'https://github.com/michael-lazar/praw3.git'


def main():

    tmpdir = tempfile.mkdtemp()
    subprocess.check_call(['git', 'clone', PRAW_REPO, tmpdir])

    # Update the commit hash reference
    os.chdir(tmpdir)
    p = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
    p.wait()
    commit = p.stdout.read().strip()
    print('Found commit %s' % commit)
    regex = 's/^__praw_hash__ =.*$/__praw_hash__ = \'%s\'/g' % commit
    packages_root = os.path.join(ROOT, 'rtv', 'packages', '__init__.py')
    print('Updating commit hash in %s' % packages_root)
    subprocess.check_call(['sed', '-i', '', regex, packages_root])

    # Overwrite the project files
    src = os.path.join(tmpdir, 'praw')
    dest = os.path.join(ROOT, 'rtv', 'packages', 'praw')
    print('Copying package files to %s' % dest)
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)

    # Cleanup
    print('Removing directory %s' % tmpdir)
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
    main()

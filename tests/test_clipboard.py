# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from rtv.clipboard import copy_linux, copy_osx
from rtv.exceptions import ProgramError


try:
    from unittest import mock
except ImportError:
    import mock


def test_copy():

    with mock.patch('subprocess.Popen') as Popen, \
            mock.patch('subprocess.call') as call:

        # Mock out the subprocess calls
        p = mock.Mock()
        p.communicate = mock.Mock()
        Popen.return_value = p

        # If the `which` command can't find a program to use
        call.return_value = 1  # Returns an error code
        with pytest.raises(ProgramError):
            copy_linux('test')

        call.return_value = 0
        copy_linux('test')
        assert Popen.call_args[0][0] == ['xsel', '-b', '-i']
        p.communicate.assert_called_with(input='test'.encode('utf-8'))
        copy_linux('test ❤')
        p.communicate.assert_called_with(input='test ❤'.encode('utf-8'))

        copy_osx('test')
        assert Popen.call_args[0][0] == ['pbcopy', 'w']
        p.communicate.assert_called_with(input='test'.encode('utf-8'))
        copy_osx('test ❤')
        p.communicate.assert_called_with(input='test ❤'.encode('utf-8'))

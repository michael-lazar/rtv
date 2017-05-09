# -*- coding: utf-8 -*-
import os
import platform
import subprocess

from .exceptions import ProgramError

def _subprocess_copy(text, args_list):
    p = subprocess.Popen(args_list, stdin=subprocess.PIPE, close_fds=True)
    p.communicate(input=text.encode('utf-8'))

def copy(text):
    """
    Copy text to OS clipboard.
    """

    if os.name == 'mac' or platform.system() == 'Darwin':
        return copy_osx(text)
    elif os.name == 'posix' or platform.system() == 'Linux':
        return copy_linux(text)
    else:
        raise NotImplementedError

def copy_osx(text):
    _subprocess_copy(text, ['pbcopy', 'w'])

def copy_linux(text):
    def get_command_name():
        # Checks for the installation of xsel or xclip
        for cmd in ['xsel', 'xclip']:
            cmd_exists = subprocess.call(
                ['which', cmd],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) is 0
            if cmd_exists:
                return cmd
        return None
    cmd_args = {'xsel' : ['xsel', '-b', '-i'],
                'xclip' : ['xclip', '-selection', 'c']}
    cmd_name = get_command_name()
    if cmd_name is None:
        raise ProgramError("External copy application not installed")
    _subprocess_copy(text, cmd_args.get(cmd_name))

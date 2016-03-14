# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import codecs
from tempfile import NamedTemporaryFile

from rtv.config import Config, copy_default_config, DEFAULT_CONFIG

try:
    from unittest import mock
except ImportError:
    import mock


def test_copy_default_config():
    "Make sure the default config file was included in the package"

    with NamedTemporaryFile(suffix='.cfg') as fp:
        with mock.patch('rtv.config.six.moves.input', return_value='y'):
            copy_default_config(fp.name)
            assert fp.read()
            permissions = os.stat(fp.name).st_mode & 0o777
            assert permissions == 0o664


def test_config_interface():
    "Test setting and removing values"

    config = Config(ascii=True)
    assert config['ascii'] is True
    config['ascii'] = False
    assert config['ascii'] is False
    config['ascii'] = None
    assert config['ascii'] is None
    del config['ascii']
    assert config['ascii'] is False

    config.update(subreddit='cfb', new_value=2.0)
    assert config['subreddit'] == 'cfb'
    assert config['new_value'] == 2.0

    assert config['link'] is None
    assert config['log'] is None


def test_config_get_args():
    "Ensure that command line arguments are parsed properly"

    args = ['rtv',
            '-s', 'cfb',
            '-l', 'https://reddit.com/permalink •',
            '--log', 'logfile.log',
            '--config', 'configfile.cfg',
            '--ascii',
            '--non-persistent',
            '--clear-auth',
            '--copy-config']

    with mock.patch('sys.argv', ['rtv']):
        config_dict = Config.get_args()
        config = Config(**config_dict)
        assert config.config == {}

    with mock.patch('sys.argv', args):
        config_dict = Config.get_args()

        config = Config(**config_dict)
        assert config['ascii'] is True
        assert config['subreddit'] == 'cfb'
        assert config['log'] == 'logfile.log'
        assert config['ascii'] is True
        assert config['persistent'] is False
        assert config['clear_auth'] is True
        assert config['link'] == 'https://reddit.com/permalink •'
        assert config['config'] == 'configfile.cfg'
        assert config['copy_config'] is True


def test_config_from_file():
    "Ensure that config file arguments are parsed properly"

    args = {
        'ascii': True,
        'persistent': False,
        'clear_auth': True,
        'log': 'logfile.log',
        'link': 'https://reddit.com/permalink •',
        'subreddit': 'cfb'}

    bindings = {
        'REFRESH': 'r, <KEY_F5>',
        'UPVOTE': ''}

    with NamedTemporaryFile(suffix='.cfg') as fp:

        fargs, fbindings = Config.get_file(filename=fp.name)
        config = Config(**fargs)
        config.keymap.set_bindings(fbindings)
        assert config.config == {}
        assert config.keymap._keymap == {}

        # [rtv]
        rows = ['{0}={1}'.format(key, val) for key, val in args.items()]
        data = '\n'.join(['[rtv]'] + rows)
        fp.write(codecs.encode(data, 'utf-8'))

        # [bindings]
        rows = ['{0}={1}'.format(key, val) for key, val in bindings.items()]
        data = '\n'.join(['', '', '[bindings]'] + rows)
        fp.write(codecs.encode(data, 'utf-8'))

        fp.flush()
        fargs, fbindings = Config.get_file(filename=fp.name)
        config.update(**fargs)
        config.keymap.set_bindings(fbindings)
        assert config.config == args
        assert config.keymap.get('REFRESH') == ['r', '<KEY_F5>']
        assert config.keymap.get('UPVOTE') == ['']


def test_config_refresh_token():
    "Ensure that the refresh token can be loaded, saved, and removed"

    with NamedTemporaryFile(delete=False) as fp:
        config = Config(token_file=fp.name)

        # Write a new token to the file
        config.refresh_token = 'secret_value'
        config.save_refresh_token()

        # Load a valid token from the file
        config.refresh_token = None
        config.load_refresh_token()
        assert config.refresh_token == 'secret_value'

        # Discard the token and delete the file
        config.delete_refresh_token()
        assert config.refresh_token is None
        assert not os.path.exists(fp.name)

        # Saving should create a new file
        config.refresh_token = 'new_value'
        config.save_refresh_token()

        # Which we can read back to verify
        config.refresh_token = None
        config.load_refresh_token()
        assert config.refresh_token == 'new_value'

        # And delete again to clean up
        config.delete_refresh_token()
        assert not os.path.exists(fp.name)

        # Loading from the non-existent file should return None
        config.refresh_token = 'secret_value'
        config.load_refresh_token()
        assert config.refresh_token is None


def test_config_history():
    "Ensure that the history can be loaded and saved"

    with NamedTemporaryFile(delete=False) as fp:
        config = Config(history_file=fp.name, history_size=3)

        config.history.add('link1')
        config.history.add('link2')
        config.history.add('link3')
        config.history.add('link4')
        assert len(config.history) == 4

        # Saving should only write the 3 most recent links
        config.save_history()
        config.load_history()
        assert len(config.history) == 3
        assert 'link1' not in config.history
        assert 'link4' in config.history

        config.delete_history()
        assert len(config.history) == 0
        assert not os.path.exists(fp.name)
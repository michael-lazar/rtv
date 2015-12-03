# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import codecs
from tempfile import NamedTemporaryFile

from rtv.config import Config

try:
    from unittest import mock
except ImportError:
    import mock


def test_config_interface():
    "Test setting and removing values"

    config = Config(ascii=True)
    assert config['ascii'] is True
    config['ascii'] = False
    assert config['ascii'] is False
    config['ascii'] = True
    del config['ascii']
    assert config['ascii'] is False
    config.update(subreddit='cfb', new_value=2.0)
    assert config['subreddit'] == 'cfb'
    assert config['new_value'] == 2.0


def test_config_from_args():
    "Ensure that command line arguments are parsed properly"

    args = ['rtv',
            '-s', 'cfb',
            '-l', 'https://reddit.com/permalink •',
            '--log', 'logfile.log',
            '--ascii',
            '--non-persistent',
            '--clear-auth']

    with mock.patch('sys.argv', ['rtv']):
        config = Config()
        config.from_args()
        assert config.config == {}

    with mock.patch('sys.argv', args):
        config = Config()
        config.from_args()
        assert config['ascii'] is True
        assert config['subreddit'] == 'cfb'
        assert config['link'] == 'https://reddit.com/permalink •'
        assert config['log'] == 'logfile.log'
        assert config['ascii'] is True
        assert config['persistent'] is False
        assert config['clear_auth'] is True


def test_config_from_file():
    "Ensure that config file arguments are parsed properly"

    args = {
        'ascii': True,
        'persistent': False,
        'clear_auth': True,
        'log': 'logfile.log',
        'link': 'https://reddit.com/permalink •',
        'subreddit': 'cfb'}

    with NamedTemporaryFile(suffix='.cfg') as fp:
        config = Config(config_file=fp.name)
        config.from_file()
        assert config.config == {}

        rows = ['{0}={1}'.format(key, val) for key, val in args.items()]
        data = '\n'.join(['[rtv]'] + rows)
        fp.write(codecs.encode(data, 'utf-8'))
        fp.flush()
        config.from_file()
        assert config.config == args


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
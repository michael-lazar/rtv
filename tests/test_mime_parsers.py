# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from rtv.mime_parsers import parsers

ARGS = 'url,modified_url,mime_type'
URLS = {
    'simple_png': (
        'http://www.example.com/i/image.png',
        'http://www.example.com/i/image.png',
        'image/png'),
    'simple_mpeg': (
        'http://www.example.com/v/video.mpeg',
        'http://www.example.com/v/video.mpeg',
        'video/mpeg'),
    'simple_unknown': (
        'http://www.example.com/i/image',
        'http://www.example.com/i/image',
        None),
    'gfycat': (
        'https://gfycat.com/DeliciousUnfortunateAdouri',
        'https://giant.gfycat.com/DeliciousUnfortunateAdouri.webm',
        'video/webm'),
    'youtube': (
        'https://www.youtube.com/watch?v=FjNdYp2gXRY',
        'https://www.youtube.com/watch?v=FjNdYp2gXRY',
        'video/x-youtube'),
    'gifv': (
        'http://i.imgur.com/i/image.gifv',
        'http://i.imgur.com/i/image.mp4',
        'video/mp4'),
    'reddit_uploads': (
        'https://i.reddituploads.com/a065472e47a4405da159189ee48bff46?fit=max'
        '&h=1536&w=1536&s=5639918a0c696b9bb3ec694dc3cf59ac',
        'https://i.reddituploads.com/a065472e47a4405da159189ee48bff46?fit=max'
        '&h=1536&w=1536&s=5639918a0c696b9bb3ec694dc3cf59ac',
        'image/jpeg'),
    'imgur_1': (
        'http://imgur.com/yW0kbMi',
        'https://i.imgur.com/yW0kbMi.jpg',
        'image/jpeg'),
    'imgur_2': (
        'http://imgur.com/yjP1v4B',
        'https://i.imgur.com/yjP1v4Bh.jpg',
        'image/jpeg'),
    'imgur_album': (
        'http://imgur.com/a/qx9t5',
        'http://i.imgur.com/uEt0YLI.jpg',
        'image/x-imgur-album'),
}


@pytest.mark.parametrize(ARGS, URLS.values(), ids=URLS.keys())
def test_parser(url, modified_url, mime_type, reddit):
    # Include the reddit fixture so the cassettes get generated

    for parser in parsers:
        if parser.pattern.match(url):
            assert parser.get_mimetype(url) == (modified_url, mime_type)
            break
    else:
        # The base parser should catch all urls before this point
        assert False

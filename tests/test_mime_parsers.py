# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from rtv.mime_parsers import parsers

URLS = [
    ('http://www.example.com/i/image.png',
     'http://www.example.com/i/image.png', 'image/png'),
    ('http://www.example.com/v/video.mpeg',
     'http://www.example.com/v/video.mpeg', 'video/mpeg'),
    ('http://www.example.com/i/image',
     'http://www.example.com/i/image', None),
    ('https://gfycat.com/DeliciousUnfortunateAdouri',
     'https://giant.gfycat.com/DeliciousUnfortunateAdouri.webm', 'video/webm'),
    ('https://www.youtube.com/watch?v=FjNdYp2gXRY',
     'https://www.youtube.com/watch?v=FjNdYp2gXRY', 'video/x-youtube'),
    ('http://i.imgur.com/i/image.gifv',
     'http://i.imgur.com/i/image.mp4', 'video/mp4'),
    ('https://i.reddituploads.com/a065472e47a4405da159189ee48bff46?fit=max&h='
     '1536&w=1536&s=5639918a0c696b9bb3ec694dc3cf59ac',
     'https://i.reddituploads.com/a065472e47a4405da159189ee48bff46?fit=max&h='
     '1536&w=1536&s=5639918a0c696b9bb3ec694dc3cf59ac', 'image/jpeg'),
    ('http://imgur.com/yW0kbMi',
     'https://i.imgur.com/yW0kbMi.jpg', 'image/jpeg'),
    ('http://imgur.com/yjP1v4B',
     'https://i.imgur.com/yjP1v4Bh.jpg', 'image/jpeg'),
    ('http://imgur.com/a/qx9t5',
     'http://i.imgur.com/uEt0YLI.jpg', 'image/x-imgur-album'),
]


@pytest.mark.parametrize('url,modified_url,mime_type', URLS)
def test_parser(url, modified_url, mime_type, reddit):
    # Add the reddit fixture so the cassettes get generated

    for parser in parsers:
        if parser.pattern.match(url):
            assert parser.get_mimetype(url) == (modified_url, mime_type)
            break
    else:
        # The base parser should catch all urls before this point
        assert False

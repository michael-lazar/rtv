# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from collections import OrderedDict

import pytest

from rtv.mime_parsers import parsers


RegexpType = type(re.compile(''))


URLS = OrderedDict([
    ('simple_png', (
        'http://www.example.com/i/image.png',  # 1. URL
        'http://www.example.com/i/image.png',  # 2. Direct media link
        'image/png')),                         # 3. MIME type of media
    ('simple_mpeg', (
        'http://www.example.com/v/video.mpeg',
        'http://www.example.com/v/video.mpeg',
        'video/mpeg')),
    ('simple_unknown', (
        'http://www.example.com/i/image',
        'http://www.example.com/i/image',
        None)),
    ('gfycat', (
        'https://gfycat.com/DeliciousUnfortunateAdouri',
        'https://giant.gfycat.com/DeliciousUnfortunateAdouri.webm',
        'video/webm')),
    ('youtube', (
        'https://www.youtube.com/watch?v=FjNdYp2gXRY',
        'https://www.youtube.com/watch?v=FjNdYp2gXRY',
        'video/x-youtube')),
    ('gifv', (
        'http://i.imgur.com/i/image.gifv',
        'http://i.imgur.com/i/image.mp4',
        'video/mp4')),
    ('reddit_uploads', (
        'https://i.reddituploads.com/a065472e47a4405da159189ee48bff46?fit=max&h=1536&w=1536&s=5639918a0c696b9bb3ec694dc3cf59ac',
        'https://i.reddituploads.com/a065472e47a4405da159189ee48bff46?fit=max&h=1536&w=1536&s=5639918a0c696b9bb3ec694dc3cf59ac',
        'image/jpeg')),
    ('imgur_1', (
        'http://imgur.com/yW0kbMi',
        'https://i.imgur.com/yW0kbMi.jpg',
        'image/jpeg')),
    ('imgur_2', (
        'http://imgur.com/yjP1v4B',
        'https://i.imgur.com/yjP1v4Bh.jpg',
        'image/jpeg')),
    ('imgur_album', (
        'http://imgur.com/a/qx9t5',
        'http://i.imgur.com/uEt0YLI.jpg',
        'image/x-imgur-album')),
    ('instagram_image', (
        'https://www.instagram.com/p/BIxQ0vrBN2Y/?taken-by=kimchi_chic',
        re.compile('https://instagram(.*)\.jpg'),
        'image/jpeg')),
    ('instagram_video', (
        'https://www.instagram.com/p/BUm3cvEhFMt/',
        re.compile('https://instagram(.*)\.mp4'),
        'video/mp4')),
    ('streamable_video', (
        'https://streamable.com/vkc0y',
        re.compile('https://(.*)\.streamablevideo\.com/video/mp4/(.*)\.mp4(.*)'),
        'video/mp4')),
    ('vidme_video', (
        'https://vid.me/rHlb',
        re.compile('https://(.*)\.cloudfront\.net/videos/15694926/52450725.mp4(.*)'),
        'video/mp4')),
])


args, ids = URLS.values(), list(URLS)
@pytest.mark.parametrize('url,modified_url,mime_type', args, ids=ids)
def test_parser(url, modified_url, mime_type, reddit):
    # Include the reddit fixture so the cassettes get generated

    for parser in parsers:
        if parser.pattern.match(url):
            parsed_url, parsed_type = parser.get_mimetype(url)
            if isinstance(modified_url, RegexpType):
                assert modified_url.match(parsed_url)
            else:
                assert modified_url == parsed_url
            assert parsed_type == mime_type
            break
    else:
        # The base parser should catch all urls before this point
        assert False

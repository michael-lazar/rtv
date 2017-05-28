# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict

import pytest

from rtv.mime_parsers import parsers

URLS = OrderedDict([
    ('simple_png', (
        'http://www.example.com/i/image.png',
        'http://www.example.com/i/image.png',
        'image/png')),
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
        'https://instagram.fsan1-1.fna.fbcdn.net/t51.2885-15/e35/13694516_861010040698614_1723649992_n.jpg?ig_cache_key=MTMxMDkwMjk1OTg4NjA5NzgxNg%3D%3D.2',
        'image/jpeg')),
    ('instagram_video', (
        'https://www.instagram.com/p/3Whn5uL5UF/',
        'https://instagram.fsan1-1.fna.fbcdn.net/t50.2886-16/11389587_1439828686321376_1437626724_n.mp4',
        'video/mp4')),
])


args, ids = URLS.values(), list(URLS)

@pytest.mark.parametrize('url,modified_url,mime_type', args, ids=ids)
def test_parser(url, modified_url, mime_type, reddit):
    # Include the reddit fixture so the cassettes get generated

    for parser in parsers:
        if parser.pattern.match(url):
            assert parser.get_mimetype(url) == (modified_url, mime_type)
            break
    else:
        # The base parser should catch all urls before this point
        assert False

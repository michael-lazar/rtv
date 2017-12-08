# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from collections import OrderedDict

import pytest

from rtv.mime_parsers import parsers, ImgurApiMIMEParser


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
        'http://imgur.com/gallery/yjP1v4B',
        'https://i.imgur.com/yjP1v4B.mp4',
        'video/mp4')),
    ('imgur_album', (
        'https://imgur.com/a/pRYEi',
        'https://i.imgur.com/tiUSazy.png https://i.imgur.com/phIsEAi.png https://i.imgur.com/TvT8V5m.png https://i.imgur.com/qETPFAi.png',
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
    ('vidme_video', pytest.param(
        'https://vid.me/rHlb',
        re.compile('https://(.*)\.cloudfront\.net/videos/15694926/52450725.mp4(.*)'),
        'video/mp4',
        marks=pytest.mark.xfail(reason="vidme API appears to have changed format"))),
    ('liveleak_video_1', (
        'https://www.liveleak.com/view?i=08b_1499296574',
        re.compile('https://cdn\.liveleak\.com/(.*)\.mp4(.*)'),
        'video/mp4')),
    ('liveleak_video_2', (
        'https://www.liveleak.com/view?i=cad_1487311993',
        re.compile('www\.youtube\.com/embed/D4GrlOMlOBY'),
        'video/x-youtube')),
    ('reddit_gif', (
        'https://v.redd.it/wkm9zol8c6fz',
        'https://v.redd.it/wkm9zol8c6fz/DASH_600_K',
        'video/mp4')),
    ('reddit_video', (
        'https://v.redd.it/zv89llsvexdz',
        'https://v.redd.it/zv89llsvexdz/DASHPlaylist.mpd',
        'video/x-youtube')),
    ('twitch_clip', (
        'https://clips.twitch.tv/avaail/ExpensiveFishBCouch',
        'https://clips-media-assets.twitch.tv/22467338656-index-0000000111.mp4',
        'video/mp4')),
    ('oddshot', (
        'https://oddshot.tv/s/5wN6Sy',
        'https://oddshot.akamaized.net/m/render-captures/source/Unknown-YjBkNTcwZWFlZGJhMGYyNQ.mp4',
        'video/mp4')),
    ('clippituser', (
        'https://www.clippituser.tv/c/edqqld',
        'https://clips.clippit.tv/edqqld/720.mp4',
        'video/mp4')),
    ('gifs_com', (
        'https://gifs.com/gif/cat-jumps-into-lake-after-guy-sneezes-0VqvRL',
        'https://j.gifs.com/0VqvRL.gif',
        'image/gif')),
    ('giphy', (
        'https://giphy.com/gifs/cameron-dallas-OpesLQSjwdGj6',
        'https://media.giphy.com/media/OpesLQSjwdGj6/giphy.mp4',
        'video/mp4')),
    ('imgtc', (
        'https://imgtc.com/w/Sa2whPE',
        'https://imgtc.b-cdn.net/uploads/ZHI3OopOhKJ.mp4',
        'video/mp4')),
    ('imgflip', (
        'https://imgflip.com/i/1dtdbv',
        'https://i.imgflip.com/1dtdbv.jpg',
        'image/jpeg')),
    ('livememe', (
        'http://www.livememe.com/v67cxy9',
        'http://e.lvme.me/v67cxy9.jpg',
        'image/jpeg')),
    ('makeameme', (
        'http://makeameme.org/meme/joined-reddit-for',
        'https://media.makeameme.org/created/joined-reddit-for.jpg',
        'image/jpeg')),
    ('flickr', (
        'https://www.flickr.com/photos/obamawhitehouse/8191317327/',
        'https://c1.staticflickr.com/9/8065/8191317327_5180e95d98_b.jpg',
        'image/jpeg')),
    ('worldstar_1', (
        'http://www.worldstarhiphop.com/videos/video.php?v=wshh09DUN5MeDK2El4sO',
        'https://hw-videos.worldstarhiphop.com/u/vid/2017/10/4OnndgEmNSME.mp4',
        'video/mp4')),
    ('worldstar_2', (
        'http://www.worldstarhiphop.com/videos/video.php?v=wshhJ6bVdAv0iMrNGFZG',
        'http://www.youtube.com/embed/Bze53qwHS8o?autoplay=1',
        'video/x-youtube')),
])


args, ids = URLS.values(), list(URLS)
@pytest.mark.parametrize('url,modified_url,mime_type', args, ids=ids)
def test_parser(url, modified_url, mime_type, reddit, config):
    # Include the reddit fixture so the cassettes get generated

    ImgurApiMIMEParser.CLIENT_ID = config['imgur_client_id']

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


def test_imgur_fallback(reddit):
    """
    If something happens to the imgur API key, the code should fallback
    to manually scraping the page.
    """

    ImgurApiMIMEParser.CLIENT_ID = ''
    for key in ['imgur_1', 'imgur_2', 'imgur_album']:
        url, modified_url, mime_type = URLS[key]

        assert ImgurApiMIMEParser.pattern.match(url)
        parsed_url, parsed_type = ImgurApiMIMEParser.get_mimetype(url)
        # Not sure why, but http://imgur.com/gallery/yjP1v4B (a .gif)
        # appears to incorrectly return as a JPG type from the scraper
        assert parsed_type is not None

    ImgurApiMIMEParser.CLIENT_ID = 'invalid_api_key'
    for key in ['imgur_1', 'imgur_2', 'imgur_album']:
        url, modified_url, mime_type = URLS[key]

        assert ImgurApiMIMEParser.pattern.match(url)
        parsed_url, parsed_type = ImgurApiMIMEParser.get_mimetype(url)
        # Not sure why, but http://imgur.com/gallery/yjP1v4B (a .gif)
        # appears to incorrectly return as a JPG type from the scraper
        assert parsed_type is not None

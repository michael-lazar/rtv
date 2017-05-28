import re
import logging
import mimetypes

import requests
from bs4 import BeautifulSoup
import json

_logger = logging.getLogger(__name__)


class BaseMIMEParser(object):
    """
    BaseMIMEParser can be sub-classed to define custom handlers for determining
    the MIME type of external urls.
    """
    pattern = re.compile(r'.*$')

    @staticmethod
    def get_mimetype(url):
        """
        Guess based on the file extension.

        Args:
            url (text): Web url that was linked to by a reddit submission.

        Returns:
            modified_url (text): The url (or filename) that will be used when
                constructing the command to run.
            content_type (text): The mime-type that will be used when
                constructing the command to run. If the mime-type is unknown,
                return None and the program will fallback to using the web
                browser.
        """
        filename = url.split('?')[0]
        content_type, _ = mimetypes.guess_type(filename)
        return url, content_type


class GfycatMIMEParser(BaseMIMEParser):
    """
    Gfycat provides a primitive json api to generate image links. URLs can be
    downloaded as either gif, webm, or mjpg. Webm was selected because it's
    fast and works with VLC.

        https://gfycat.com/api

        https://gfycat.com/UntidyAcidicIberianemeraldlizard -->
        https://giant.gfycat.com/UntidyAcidicIberianemeraldlizard.webm
    """
    pattern = re.compile(r'https?://(www\.)?gfycat\.com/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        parts = url.split('/')
        api_url = '/'.join(parts[:-1] + ['cajax', 'get'] + parts[-1:])
        resp = requests.get(api_url)
        image_url = resp.json()['gfyItem']['webmUrl']
        return image_url, 'video/webm'


class YoutubeMIMEParser(BaseMIMEParser):
    """
    Youtube videos can be streamed with vlc or downloaded with youtube-dl.
    Assign a custom mime-type so they can be referenced in mailcap.
    """
    pattern = re.compile(
        r'(?:https?://)?(m\.)?(?:youtu\.be/|(?:www\.)?youtube\.com/watch'
        r'(?:\.php)?\'?.*v=)([a-zA-Z0-9\-_]+)')

    @staticmethod
    def get_mimetype(url):
        return url, 'video/x-youtube'


class GifvMIMEParser(BaseMIMEParser):
    """
    Special case for .gifv, which is a custom video format for imgur serves
    as html with a special <video> frame. Note that attempting for download as
    .webm also returns this html page. However, .mp4 appears to return the raw
    video file.
    """
    pattern = re.compile(r'.*[.]gifv$')

    @staticmethod
    def get_mimetype(url):
        modified_url = url[:-4] + 'mp4'
        return modified_url, 'video/mp4'


class RedditUploadsMIMEParser(BaseMIMEParser):
    """
    Reddit uploads do not have a file extension, but we can grab the mime-type
    from the page header.
    """
    pattern = re.compile(r'https://i\.reddituploads\.com/.+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.head(url)
        content_type = page.headers.get('Content-Type', '')
        content_type = content_type.split(';')[0]  # Strip out the encoding
        return url, content_type


class ImgurMIMEParser(BaseMIMEParser):
    """
    Imgur provides a json api exposing its entire infrastructure. Each imgur
    page has an associated hash and can either contain an album, a gallery, or single image.

    see https://apidocs.imgur.com
    """
    pattern = re.compile(r'https?://(w+\.)?(m\.)?imgur\.com/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        endpoint = 'https://api.imgur.com/3/{domain}/{page_hash}'
        header = {'authorization': 'Client-ID {}'.format('d8842d573e8b9dd')}

        pattern = re.compile(r'https?://(w+\.)?(m\.)?imgur\.com/((?P<domain>a|album|gallery)/)?(?P<hash>.+)$')
        m = pattern.match(url)
        page_hash = m.group('hash')
        domain = 'album' if m.group('domain') in ['a', 'album'] else 'gallery'

        r = requests.get(endpoint.format(domain=domain, page_hash=page_hash),
                                         headers=header)
        if r.status_code == 404:
            r = requests.get(endpoint.format(domain='image',
                                page_hash=page_hash), headers=header)

        data = json.loads(r.text)['data']
        if 'images' in data:
            # TODO: handle imgur albums with mixed content, i.e. jpeg and gifv
            urls = ' '.join([d['link'] for d in data['images'] if not d['animated']])
            return urls, 'image/x-imgur-album'
        else:
            return (data['mp4'], 'video/mp4') if data['animated'] else (data['link'], data['type'])

        return url, None


class InstagramMIMEParser(BaseMIMEParser):
    """
    Instagram pages can contain either an embedded image or video. The <meta>
    tags below provide the relevant info.

    <meta property="og:image" content="https://xxxx.jpg?ig_cache_key=xxxxx" />
    <meta property="og:video:secure_url" content="https://xxxxx.mp4" />

    If the page is a video page both of the above tags will be present.
    """
    pattern = re.compile(r'https?://(www\.)?instagr((am\.com)|\.am)/p/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        tag = soup.find('meta', attrs={'property': 'og:video:secure_url'})
        tag = tag or soup.find('meta', attrs={'property':  'og:image'})
        if tag:
            return BaseMIMEParser.get_mimetype(tag.get('content'))
        else:
            return url, None


# Parsers should be listed in the order they will be checked
parsers = [
    InstagramMIMEParser,
    GfycatMIMEParser,
    ImgurMIMEParser,
    RedditUploadsMIMEParser,
    YoutubeMIMEParser,
    GifvMIMEParser,
    BaseMIMEParser]

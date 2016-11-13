import re
import logging
import mimetypes

import requests
from bs4 import BeautifulSoup

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
    The majority of imgur links don't point directly to the image, so we need
    to open the provided url and scrape the page for the link.

    Scrape the actual image url from an imgur landing page. Imgur intentionally
    obscures this on most reddit links in order to draw more traffic for their
    advertisements.

    There are a couple of <meta> tags that supply the relevant info:
        <meta name="twitter:image" content="https://i.imgur.com/xrqQ4LEh.jpg">
        <meta property="og:image" content="http://i.imgur.com/xrqQ4LE.jpg?fb">
        <link rel="image_src" href="http://i.imgur.com/xrqQ4LE.jpg">
    """
    pattern = re.compile(r'https?://(w+\.)?(m\.)?imgur\.com/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        tag = soup.find('meta', attrs={'name': 'twitter:image'})
        if tag:
            url = tag.get('content')
            if GifvMIMEParser.pattern.match(url):
                return GifvMIMEParser.get_mimetype(url)
        return BaseMIMEParser.get_mimetype(url)


class ImgurAlbumMIMEParser(BaseMIMEParser):
    """
    Imgur albums can contain several images, which need to be scraped from the
    landing page. Assumes the following html structure:

        <div class="post-image">
            <a href="//i.imgur.com/L3Lfp1O.jpg" class="zoom">
                <img class="post-image-placeholder"
                     src="//i.imgur.com/L3Lfp1Og.jpg" alt="Close up">
                <img class="js-post-image-thumb"
                     src="//i.imgur.com/L3Lfp1Og.jpg" alt="Close up">
            </a>
        </div>
    """
    pattern = re.compile(r'https?://(w+\.)?(m\.)?imgur\.com/a(lbum)?/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        urls = []
        for div in soup.find_all('div', class_='post-image'):
            img = div.find('img')
            src = img.get('src') if img else None
            if src:
                urls.append('http:{0}'.format(src))

        if urls:
            return " ".join(urls), 'image/x-imgur-album'
        else:
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
    ImgurAlbumMIMEParser,
    ImgurMIMEParser,
    RedditUploadsMIMEParser,
    YoutubeMIMEParser,
    GifvMIMEParser,
    BaseMIMEParser]

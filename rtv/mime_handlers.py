import re
import mimetypes
from html.parser import HTMLParser

import requests


class HTMLParsed(Exception):
    def __init__(self, data):
        self.data = data


class BaseHandler(object):
    """
    BaseHandler can be sub-classed to define custom handlers for determining
    the MIME type of external urls.
    """

    # URL regex pattern that the handler will be triggered on
    pattern = re.compile(r'.*$')

    @staticmethod
    def get_mimetype(url):
        """
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

        # Guess based on the file extension
        filename = url.split('?')[0]
        content_type, _ = mimetypes.guess_type(filename)
        return url, content_type


class YoutubeHandler(BaseHandler):
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


class GifvHandler(BaseHandler):
    """
    Special case for .gifv, which is a custom video format for imgur that is
    incorrectly (or on purpose?) returned with a Content-Type of text/html.
    """
    pattern = re.compile(r'.*[.]gifv$')

    @staticmethod
    def get_mimetype(url):
        modified_url = url[:-4] + 'webm'
        return modified_url, 'video/webm'


class RedditUploadsHandler(BaseHandler):
    """
    Reddit uploads do not have a file extension, but we can grab the mime-type
    from the page header.
    """
    pattern = re.compile(r'https://i.reddituploads.com/.+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.head(url)
        content_type = page.headers.get('Content-Type', '')
        content_type = content_type.split(';')[0]  # Strip out the encoding
        return url, content_type


class ImgurHTMLParser(HTMLParser):
    """
    Scrape the actual image url from an imgur landing page. Imgur intentionally
    obscures this on most reddit links in order to draw more traffic for their
    advertisements.

    There are a couple of <meta> tags that supply the relevant info:
        <meta name="twitter:image" content="https://i.imgur.com/xrqQ4LEh.jpg">
        <meta property="og:image" content="http://i.imgur.com/xrqQ4LE.jpg?fb">
        <link rel="image_src" href="http://i.imgur.com/xrqQ4LE.jpg">

    Note:
        BeautifulSoup or lxml would be faster here but I wanted to skip adding
        an extra dependency for something as trivial as this.
    """

    def handle_starttag(self, tag, attr):
        if tag == 'meta' and attr[0] == ('name', 'twitter:image'):
            raise HTMLParsed(attr[1][1])


class ImgurHandler(BaseHandler):
    """
    The majority of imgur links don't point directly to the image, so we need
    to open the provided url and scrape the page for the link. For galleries,
    this method only returns the first image.
    """
    pattern = re.compile(r'https?://(w+\.)?(m\.)?imgur\.com/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        imgur_page = requests.get(url)
        try:
            ImgurHTMLParser().feed(imgur_page.text)
        except HTMLParsed as data:
            # We found a link
            url = data.data
            if GifvHandler.pattern.match(url):
                return GifvHandler.get_mimetype(url)

        return BaseHandler.get_mimetype(url)


# Handlers should be defined in the order they will be checked
handlers = [
    ImgurHandler,
    RedditUploadsHandler,
    YoutubeHandler,
    GifvHandler,
    BaseHandler]

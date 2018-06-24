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
        filename = filename.split('#')[0]
        content_type, _ = mimetypes.guess_type(filename)
        return url, content_type


class OpenGraphMIMEParser(BaseMIMEParser):
    """
    Open graph protocol is used on many web pages.

    <meta property="og:image" content="https://xxxx.jpg?ig_cache_key=xxxxx" />
    <meta property="og:video:secure_url" content="https://xxxxx.mp4" />

    If the page is a video page both of the above tags will be present and
    priority is given to video content.

    see http://ogp.me
    """
    pattern = re.compile(r'.*$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        for og_type in ['video', 'image']:
            prop = 'og:' + og_type + ':secure_url'
            tag = soup.find('meta', attrs={'property': prop})
            if not tag:
                prop = 'og:' + og_type
                tag = soup.find('meta', attrs={'property': prop})
            if tag:
                return BaseMIMEParser.get_mimetype(tag.get('content'))

        return url, None


class VideoTagMIMEParser(BaseMIMEParser):
    """
    <video width="320" height="240" controls>
        <source src="movie.mp4" res="HD" type="video/mp4">
        <source src="movie.mp4" res="SD" type="video/mp4">
        <source src="movie.ogg" type="video/ogg">
    </video>
    """
    pattern = re.compile(r'.*$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        # TODO: Handle pages with multiple videos
        video = soup.find('video')
        if video:
            source = video.find('source', attr={'res': 'HD'})
            source = source or video.find('source', attr={'type': 'video/mp4'})
            source = source or video.find('source')
        if source:
            return source.get('src'), source.get('type')
        else:
            return url, None


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
        parts = url.replace('gifs/detail/', '').split('/')
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


class VimeoMIMEParser(BaseMIMEParser):
    """
    Vimeo videos can be streamed with vlc or downloaded with youtube-dl.
    Assign a custom mime-type so they can be referenced in mailcap.
    """
    pattern = re.compile(r'https?://(www\.)?vimeo\.com/\d+$')

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


class RedditVideoMIMEParser(BaseMIMEParser):
    """
    Reddit hosted videos/gifs.
    Media uses MPEG-DASH format (.mpd)
    """
    pattern = re.compile(r'https://v\.redd\.it/.+$')

    @staticmethod
    def get_mimetype(url):
        request_url = url + '/DASHPlaylist.mpd'
        page = requests.get(request_url)
        soup = BeautifulSoup(page.content, 'html.parser')
        if not soup.find('representation', attrs={'mimetype': 'audio/mp4'}):
            reps = soup.find_all('representation',
                                 attrs={'mimetype': 'video/mp4'})
            rep = sorted(reps, reverse=True,
                         key=lambda t: int(t.get('bandwidth')))[0]
            return url + '/' + rep.find('baseurl').text, 'video/mp4'

        return request_url, 'video/x-youtube'


class ImgurApiMIMEParser(BaseMIMEParser):
    """
    Imgur now provides a json API exposing its entire infrastructure. Each Imgur
    page has an associated hash and can either contain an album, a gallery,
    or single image.

    The default client token for RTV is shared among users and allows a maximum
    global number of requests per day of 12,500. If we find that this limit is
    not sufficient for all of rtv's traffic, this method will be revisited.

    Reference:
        https://apidocs.imgur.com
    """
    CLIENT_ID = None
    pattern = re.compile(
        r'https?://(w+\.)?(m\.)?imgur\.com/'
        r'((?P<domain>a|album|gallery)/)?(?P<hash>[a-zA-Z0-9]+)$')

    @classmethod
    def get_mimetype(cls, url):

        endpoint = 'https://api.imgur.com/3/{domain}/{page_hash}'
        headers = {'authorization': 'Client-ID {0}'.format(cls.CLIENT_ID)}

        m = cls.pattern.match(url)
        page_hash = m.group('hash')

        if m.group('domain') in ('a', 'album'):
            domain = 'album'
        else:
            # This could be a gallery or a single image, but there doesn't
            # seem to be a way to reliably distinguish between the two.
            # Assume a gallery, which appears to be more common, and fallback
            # to an image request upon failure.
            domain = 'gallery'

        if not cls.CLIENT_ID:
            return cls.fallback(url, domain)

        api_url = endpoint.format(domain=domain, page_hash=page_hash)
        r = requests.get(api_url, headers=headers)

        if domain == 'gallery' and r.status_code != 200:
            # Not a gallery, try to download using the image endpoint
            api_url = endpoint.format(domain='image', page_hash=page_hash)
            r = requests.get(api_url, headers=headers)

        if r.status_code != 200:
            _logger.warning('Imgur API failure, status %s', r.status_code)
            return cls.fallback(url, domain)

        data = r.json().get('data')
        if not data:
            _logger.warning('Imgur API failure, resp %s', r.json())
            return cls.fallback(url, domain)

        if 'images' in data and len(data['images']) > 1:
            # TODO: handle imgur albums with mixed content, i.e. jpeg and gifv
            link = ' '.join([d['link'] for d in data['images'] if not d['animated']])
            mime = 'image/x-imgur-album'
        else:
            data = data['images'][0] if 'images' in data else data
            # this handles single image galleries

            link = data['mp4'] if data['animated'] else data['link']
            mime = 'video/mp4' if data['animated'] else data['type']

        link = link.replace('http://', 'https://')
        return link, mime

    @classmethod
    def fallback(cls, url, domain):
        """
        Attempt to use one of the scrapers if the API doesn't work
        """
        if domain == 'album':
            return ImgurScrapeAlbumMIMEParser.get_mimetype(url)
        else:
            return ImgurScrapeMIMEParser.get_mimetype(url)


class ImgurScrapeMIMEParser(BaseMIMEParser):
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


class ImgurScrapeAlbumMIMEParser(BaseMIMEParser):
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

        return url, None


class InstagramMIMEParser(OpenGraphMIMEParser):
    """
    Instagram uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?instagr((am\.com)|\.am)/p/[^.]+$')


class StreamableMIMEParser(OpenGraphMIMEParser):
    """
    Streamable uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?streamable\.com/[^.]+$')


class TwitchMIMEParser(BaseMIMEParser):
    """
    Non-streaming videos hosted by twitch.tv
    """
    pattern = re.compile(r'https?://clips\.?twitch\.tv/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        tag = soup.find('meta', attrs={'name': 'twitter:image'})
        thumbnail = tag.get('content')
        suffix = '-preview.jpg'
        if thumbnail.endswith(suffix):
            return thumbnail.replace(suffix, '.mp4'), 'video/mp4'

        return url, None


class OddshotMIMEParser(OpenGraphMIMEParser):
    """
    Oddshot uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://oddshot\.tv/s(hot)?/[^.]+$')


class VidmeMIMEParser(BaseMIMEParser):
    """
    Vidme provides a json api.

    https://doc.vid.me
    """
    pattern = re.compile(r'https?://(www\.)?vid\.me/[^.]+$')

    @staticmethod
    def get_mimetype(url):
        resp = requests.get('https://api.vid.me/videoByUrl?url=' + url)
        if resp.status_code == 200 and resp.json()['status']:
            return resp.json()['video']['complete_url'], 'video/mp4'

        return url, None


class LiveleakMIMEParser(BaseMIMEParser):
    """
    https://www.liveleak.com/view?i=12c_3456789
    <video>
        <source src="https://cdn.liveleak.com/..mp4" res="HD" type="video/mp4">
        <source src="https://cdn.liveleak.com/..mp4" res="SD" type="video/mp4">
    </video>
    Sometimes only one video source is available
    """
    pattern = re.compile(r'https?://((www|m)\.)?liveleak\.com/view\?i=\w+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        urls = []
        videos = soup.find_all('video')
        for vid in videos:
            source = vid.find('source', attr={'res': 'HD'})
            source = source or vid.find('source')
            if source:
                urls.append((source.get('src'), source.get('type')))

        # TODO: Handle pages with multiple videos
        if urls:
            return urls[0]

        def filter_iframe(t):
            return t.name == 'iframe' and 'youtube.com' in t['src']

        iframe = soup.find_all(filter_iframe)
        if iframe:
            return YoutubeMIMEParser.get_mimetype(iframe[0]['src'].strip('/'))

        return url, None


class ClippitUserMIMEParser(BaseMIMEParser):
    """
    Clippit uses a video player container
    """
    pattern = re.compile(r'https?://(www\.)?clippituser\.tv/c/.+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        tag = soup.find(id='jwplayer-container')
        quality = ['data-{}-file'.format(_) for _ in ['hd', 'sd']]
        return tag.get(quality[0]), 'video/mp4'


class GifsMIMEParser(OpenGraphMIMEParser):
    """
    Gifs.com uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?gifs\.com/gif/.+$')


class GiphyMIMEParser(OpenGraphMIMEParser):
    """
    Giphy.com uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?giphy\.com/gifs/.+$')


class ImgtcMIMEParser(OpenGraphMIMEParser):
    """
    imgtc.com uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?imgtc\.com/w/.+$')


class ImgflipMIMEParser(OpenGraphMIMEParser):
    """
    imgflip.com uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?imgflip\.com/i/.+$')


class LivememeMIMEParser(OpenGraphMIMEParser):
    """
    livememe.com uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?livememe\.com/[^.]+$')


class MakeamemeMIMEParser(OpenGraphMIMEParser):
    """
    makeameme.com uses the Open Graph protocol
    """
    pattern = re.compile(r'https?://(www\.)?makeameme\.org/meme/.+$')


class FlickrMIMEParser(OpenGraphMIMEParser):
    """
    Flickr uses the Open Graph protocol
    """
    # TODO: handle albums/photosets (https://www.flickr.com/services/api)
    pattern = re.compile(r'https?://(www\.)?flickr\.com/photos/[^/]+/[^/]+/?$')


class StreamjaMIMEParser(VideoTagMIMEParser):
    """
    Embedded HTML5 video element
    """
    pattern = re.compile(r'https?://(www\.)?streamja\.com/[^/]+/?$')


class WorldStarHipHopMIMEParser(BaseMIMEParser):
    """
    <video>
        <source src="https://hw-mobile.worldstarhiphop.com/..mp4" type="video/mp4">
        <source src="" type="video/mp4">
    </video>
    Sometimes only one video source is available
    """
    pattern = re.compile(r'https?://((www|m)\.)?worldstarhiphop\.com/videos/video.php\?v=\w+$')

    @staticmethod
    def get_mimetype(url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        def filter_source(t):
            return t.name == 'source' and t['src'] and t['type'] == 'video/mp4'

        source = soup.find_all(filter_source)
        if source:
            return source[0]['src'], 'video/mp4'

        def filter_iframe(t):
            return t.name == 'iframe' and 'youtube.com' in t['src']

        iframe = soup.find_all(filter_iframe)
        if iframe:
            return YoutubeMIMEParser.get_mimetype(iframe[0]['src'])

        return url, None


# Parsers should be listed in the order they will be checked
parsers = [
    StreamjaMIMEParser,
    ClippitUserMIMEParser,
    OddshotMIMEParser,
    StreamableMIMEParser,
    VidmeMIMEParser,
    InstagramMIMEParser,
    GfycatMIMEParser,
    ImgurApiMIMEParser,
    RedditUploadsMIMEParser,
    RedditVideoMIMEParser,
    YoutubeMIMEParser,
    VimeoMIMEParser,
    LiveleakMIMEParser,
    TwitchMIMEParser,
    FlickrMIMEParser,
    GifsMIMEParser,
    GiphyMIMEParser,
    ImgtcMIMEParser,
    ImgflipMIMEParser,
    LivememeMIMEParser,
    MakeamemeMIMEParser,
    WorldStarHipHopMIMEParser,
    GifvMIMEParser,
    BaseMIMEParser]

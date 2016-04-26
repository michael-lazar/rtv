import os
import logging
from tempfile import NamedTemporaryFile
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError

import requests
from praw.objects import Submission

from .config import THUMBS, MEDIA_CACHE

_logger = logging.getLogger(__name__)


class MediaCache(object):

    default_thumbs = {
        '': os.path.join(THUMBS, 'default.png'),
        'default': os.path.join(THUMBS, 'default.png'),
        'nsfw': os.path.join(THUMBS, 'nsfw.png'),
        'self': os.path.join(THUMBS, 'self.png'),
    }

    def __init__(self, cache_size=200, cache_dir=MEDIA_CACHE):

        self._cache_size = cache_size
        self._cache_dir = cache_dir

        self._cache = OrderedDict()
        self._pool = ThreadPoolExecutor(max_workers=15)

        # Redirect all newly loaded submissions to pass through this instance.
        if not hasattr(Submission, 'from_api_response_'):
            Submission.from_api_response_ = Submission.from_api_response
        Submission.from_api_response = self._hook_submission_load

        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def __del__(self):
        for fp in self._cache.values():
            if hasattr(fp, 'close'):
                fp.close()  # Clean up the temporary file

    def preload(self, urls):
        """
        Initiate batch loading of images in the background. This should be
        called as soon as the image urls become available.
        """

        for url in urls:
            if url in self._cache:
                # Move the entry to the front of the cache
                self._cache[url] = self._cache.pop(url)
            else:
                self._cache[url] = self._pool.submit(self._load_url, url)

        # Trim the oldest entries from the cache
        while len(self._cache) >= self._cache_size:
            fp = self._cache.popitem(last=False)
            if hasattr(fp, 'close'):
                fp.close()  # Clean up the temporary file

    def get_image_files(self, urls):
        """
        Return a list of temporary images files corresponding to the given urls.
        This will block until all of the requested files have finished loading.
        """

        self.preload(urls)

        out = []
        for url in urls:
            try:
                fp = self._cache[url].result(timeout=3)
            except TimeoutError:
                filename = self.default_thumbs['default']
            else:
                if hasattr(fp, 'name'):
                    filename = fp.name
                else:
                    filename = fp
            out.append(filename)
        return out

    def _load_url(self, url):

        if url in self.default_thumbs:
            return self.default_thumbs[url]

        try:
            resp = requests.get(url, timeout=5)
        except requests.RequestException:
            return self.default_thumbs['default']
        else:
            suffix = os.path.splitext(url)[1]
            fp = NamedTemporaryFile(suffix=suffix, dir=MEDIA_CACHE)
            fp.write(resp.content)
            fp.flush()
            return fp

    def _hook_submission_load(self, *args, **kwargs):
        """
        Hook into the Submission.from_api_response in order to trigger an
        immediate action for every loaded submission. This is a workaround to
        deal with the limitation that reddit.get_content() generators don't
        notify when a new batch of submissions is loaded.
        """
        submission = Submission.from_api_response_(*args, **kwargs)
        self.preload([submission.thumbnail])
        return submission
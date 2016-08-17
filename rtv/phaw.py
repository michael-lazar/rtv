"""
Python HackerNews Api Wrapper
"""
import weakref
import logging

import requests
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class HackerNews(object):

    DOMAIN = 'https://news.ycombinator.com/'

    def __init__(self):
        self.session = requests.Session()
        self.user = None

    def login(self, username, password):
        payload = {'acct': username, 'pw': password}
        resp = self.session.post(self.DOMAIN + 'login', data=payload)
        resp.raise_for_status()
        self.user = username

    def logout(self):
        self.session.cookies.clear()
        self.user = None

    def get_top(self):
        return self._get_listings(self.DOMAIN + 'news')

    def get_new(self):
        return self._get_listings(self.DOMAIN + 'newest')

    def get_best(self):
        return self._get_listings(self.DOMAIN + 'best')

    def get_show(self):
        return self._get_listings(self.DOMAIN + 'show')

    def get_ask(self):
        return self._get_listings(self.DOMAIN + 'ask')

    def get_jobs(self):
        return self._get_listings(self.DOMAIN + 'jobs')

    def get_submission(self, item_id):
        """
        Retrieve a single submission with all of the comments
        """
        submission = HNSubmission(self, id=id)
        submission.load_comments()
        return submission

    def _get_listings(self, url):
        """
        Returns a generator that will paginate submissions for the given url.
        """

        while True:
            resp = self.session.get(url)
            resp.raise_for_status()

            data = self.scrape_listing_page(resp.content)
            for sub in data['submissions']:
                yield HNSubmission(self, **item)

            if data['more']:
                url = self.DOMAIN + data['more']
            else:
                break

    @staticmethod
    def scrape_submission_page(html):
        data = {}
        data['submission'] = None
        data['comments'] = []
        return data

    @staticmethod
    def scrape_listing_page(html):
        data = {}

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='itemlist')

        data['submissions'] = []
        for row in table.find_all('tr', class_='athing'):
            sub = {}
            sub['id'] = row['id']

            votelinks = row.find('td', class_='votelinks')
            vote_link = votelinks.find('a') if votelinks else None
            sub['vote_href'] = vote_link['href'] if vote_link else None
            sub['liked'] = vote_link['class'] == 'nosee'

            title = row.find_all('td')[-1]
            storylink = title.find('a', class_='storylink')
            sitestr = title.find('span', class_='sitestr')
            sub['url'] = storylink['href'] if storylink else None
            sub['title'] = storylink.text if storylink else None
            sub['domain'] = sitestr.text if sitestr else None

            body = row.next_sibling
            score = body.find('span', class_='score')
            user = body.find('a', class_='hnuser')
            age = body.find('span', class_='age')
            comments = body.find_all('a')
            comments = comments[2] if len(comments) == 3 else None

            sub['score'] = score.text if score else None
            sub['author'] = user.text if user else None
            sub['age'] = age.text if age else None
            sub['count'] = comments.text if comments else None

            data['submissions'].append(sub)

        more = soup.find('a', class_='morelink')
        data['more'] = more['href'] if more else None
        return data


class HNSubmission(object):

    def __init__(self, hn, id, url=None, title=None, domain=None,
                 score=None, author=None, age=None, count=None,
                 vote_href=None):

        self.hn = weakref.proxy(hn)

        self.id = id
        self.url = url
        self.title = title
        self.domain = domain
        self.score = score
        self.author = author
        self.age = age
        self.count = count
        self.vote_href = vote_href
        self.comments = []

        self.liked = False

    def load_comments(self):
        payload = {'id': self.id}
        resp = self.hn.session.get(self.hn.DOMAIN + 'item', params=payload)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, 'html.parser')

    def upvote(self):
        """
        Upvote the current submission
        """

        resp = self.hn.session.get(self.hn.DOMAIN + self.vote_href)
        resp.raise_for_status()
        self.liked = True


class HNComment(object):

    def __init__(self, hn, id=None):

        self.hn = weakref.proxy(hn)

    def upvote(self):
        pass


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s')

    hn = HackerNews()
    for item in hn.get_top():
        print(item)
        item.load_comments()

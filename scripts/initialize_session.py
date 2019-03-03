"""
Initialize an authenticated instance of PRAW to interact with.

$ python -i initialize_session.py
"""
from rtv.docs import AGENT
from rtv.packages import praw
from rtv.content import RequestHeaderRateLimiter
from rtv.config import Config

config = Config()
config.load_refresh_token()

reddit = praw.Reddit(
    user_agent=AGENT.format(version='test_session'),
    decode_html_entities=False,
    disable_update_check=True,
    timeout=10,  # 10 second request timeout
    handler=RequestHeaderRateLimiter())


reddit.set_oauth_app_info(
    config['oauth_client_id'],
    config['oauth_client_secret'],
    config['oauth_redirect_uri'])
reddit.refresh_access_information(config.refresh_token)

inbox = reddit.get_inbox()
items = [next(inbox) for _ in range(20)]
pass
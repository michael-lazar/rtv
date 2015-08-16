import configparser
import os
import webbrowser
import uuid

__all__ = []

def get_config_file_path():
    HOME = os.path.expanduser('~')
    XDG_CONFIG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
    config_paths = [
        os.path.join(XDG_CONFIG_HOME, 'rtv', 'rtv.cfg'),
        os.path.join(HOME, '.rtv')
    ]

    # get the first existing config file
    for config_path in config_paths:
        if os.path.exists(config_path):
            break

    return config_path

def load_oauth_config():
    config = configparser.ConfigParser()
    config_path = get_config_file_path()
    config.read(config_path)

    return config

def read_setting(key, section='oauth'):
    config = load_oauth_config()

    try:
        setting = config[section][key]
    except KeyError:
        return None

    return setting

def write_setting(key, value, section='oauth'):
    config = load_oauth_config()

    config[section][key] = value
    with open(config_path, 'w') as cfg_file:
        config.write(cfg_file)

def authorize(reddit):
    config = load_oauth_config()

    settings = {}
    if config.has_section('oauth'):
        settings = dict(config.items('oauth'))

    scopes = ["edit", "history", "identity", "mysubreddits", "privatemessages", "read", "report", "save", "submit", "subscribe", "vote"]

    reddit.set_oauth_app_info(settings['client_id'],
                              settings['client_secret'],
                              settings['redirect_uri'])

    # Generate a random UUID
    hex_uuid = uuid.uuid4().hex

    permission_ask_page_link = reddit.get_authorize_url(str(hex_uuid), scope=scopes, refreshable=True)
    input("You will now be redirected to your web browser. Press Enter to continue.")
    webbrowser.open(permission_ask_page_link)

    print("After allowing rtv app access, you will land on a page giving you a state and a code string. Please enter them here.")
    final_state = input("State : ")
    final_code = input("Code : ")

    # Check if UUID matches obtained state
    # (if not, authorization process is compromised, and I'm giving up)
    if hex_uuid == final_state:
        print("Obtained state matches UUID")
    else:
        print("Obtained state does not match UUID, stopping.")
        return

    # Get access information (authorization token)
    info = reddit.get_access_information(final_code)
    config['oauth']['authorization_token'] = info['access_token']
    config['oauth']['refresh_token'] = info['refresh_token']
    config['oauth']['scope'] = '-'.join(info['scope'])

    config_path = get_config_file_path()
    with open(config_path, 'w') as cfg_file:
        config.write(cfg_file)

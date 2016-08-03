# todo: migrate from hacked session to actual session..

from twisted.web.server import Session


from yombo.core.log import get_logger

logger = get_logger("library.webconfig.session")


class YomboSession(Session):
    sessionTimeout = 5

    def __init__(self, site, uid, reactor=None):

        super(SQLDictionary, self).__init__()  # Call parent's __init__ function first.
        self.config = DictObject({
            'cookie_name': 'yombo_' + self._Configs.get('webinterface', 'cookie_suffix', random_string(length=30)),
            'cookie_domain': None,
            'cookie_path' : '/',
            'max_session': 15552000,  # How long session can be good for: 180 days
            'max_idle': 5184000,  # Max idle timeout: 60 days
            'max_session_no_auth': 600,  # If not auth in 10 mins, delete session
            'ignore_expiry': True,
            'ignore_change_ip': True,
            'expired_message': 'Session expired',
            'httponly': True,
            'secure': False,  # will change to true after SSL system/dns complete. - Mitch
        })



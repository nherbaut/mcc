import requests
from mcr.libsettings import *


# wrapp base url and credentials to monkey-patched session object
class SessionWithUrlBase(requests.Session):
    def __init__(self, url_base, login, pwd, *args, **kwargs):
        super(SessionWithUrlBase, self).__init__(*args, **kwargs)
        self.url_base = url_base
        self.auth = (login, pwd)

    def request(self, method, url, **kwargs):
        modified_url = self.url_base + url
        return super(SessionWithUrlBase, self).request(method, modified_url, **kwargs)


requests.Session = SessionWithUrlBase
session = requests.Session(settings_api_url, settings_login, settings_pwd)

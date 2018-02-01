import requests
import logging
from requests.adapters import HTTPAdapter


class DummyAdaptor(HTTPAdapter):
    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None, proxies=None):
        logging.debug(request.url)
        return super(DummyAdaptor, self).send(request, stream=stream, timeout=timeout, verify=verify,
                                              cert=cert, proxies=proxies)


# wrapp base url and credentials to monkey-patched session object
class SessionWithUrlBase(requests.Session):
    def __init__(self, url_base, login, pwd, *args, **kwargs):
        super(SessionWithUrlBase, self).__init__(*args, **kwargs)
        self.url_base = url_base
        self.auth = (login, pwd)

    def request(self, method, url, **kwargs):
        modified_url = self.url_base + url
        return super(SessionWithUrlBase, self).request(method, modified_url, **kwargs)

    def get_adapter(self, url):
        return DummyAdaptor()


def create_session(settings_api_url, settings_login, settings_pwd):
    requests.Session = SessionWithUrlBase
    session = requests.Session(settings_api_url, settings_login, settings_pwd)
    return session

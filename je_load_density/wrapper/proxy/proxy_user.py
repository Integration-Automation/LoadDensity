from je_load_density.wrapper.proxy.user.fast_http_user_proxy import ProxyFastHTTPUser
from je_load_density.wrapper.proxy.user.sequence_user_proxy import ProxySequenceUser


class LocustUserProxy(object):

    def __init__(self):
        self.user_dict = dict()
        self.user_dict.update(
            {
                "fast_http_user": ProxyFastHTTPUser(),
                "sequence_user": ProxySequenceUser()
            }
        )


locust_wrapper_proxy = LocustUserProxy()

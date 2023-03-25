class ProxyFastHTTPUser(object):

    def __init__(self):
        self.user_detail_dict = None
        self.request_method = None
        self.request_url = None

    def setting(self, user_detail_dict: dict):
        self.user_detail_dict = user_detail_dict
        self.request_method = user_detail_dict.get("request_method", "get")
        self.request_url = user_detail_dict.get("request_url", "/")
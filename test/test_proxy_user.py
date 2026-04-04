from je_load_density.wrapper.proxy.user.http_user_proxy import ProxyHTTPUser
from je_load_density.wrapper.proxy.user.fast_http_user_proxy import ProxyFastHTTPUser
from je_load_density.wrapper.proxy.proxy_user import LocustUserProxy


class TestProxyHTTPUser:

    def test_init_defaults(self):
        user = ProxyHTTPUser()
        assert user.user_detail_dict is None
        assert user.tasks is None

    def test_configure(self):
        user = ProxyHTTPUser()
        detail = {"user": "http_user", "host": "http://localhost"}
        tasks = {
            "get": {"request_url": "http://example.com/get"},
            "post": {"request_url": "http://example.com/post"},
        }
        user.configure(detail, tasks)
        assert user.user_detail_dict == detail
        assert user.tasks == tasks

    def test_configure_overwrite(self):
        user = ProxyHTTPUser()
        user.configure({"user": "a"}, {"get": {"request_url": "/a"}})
        user.configure({"user": "b"}, {"post": {"request_url": "/b"}})
        assert user.user_detail_dict["user"] == "b"
        assert "post" in user.tasks
        assert "get" not in user.tasks


class TestProxyFastHTTPUser:

    def test_init_defaults(self):
        user = ProxyFastHTTPUser()
        assert user.user_detail_dict is None
        assert user.tasks is None

    def test_configure(self):
        user = ProxyFastHTTPUser()
        detail = {"user": "fast_http_user"}
        tasks = {"get": {"request_url": "http://example.com"}}
        user.configure(detail, tasks)
        assert user.user_detail_dict == detail
        assert user.tasks == tasks


class TestLocustUserProxy:

    def test_init_has_both_users(self):
        proxy = LocustUserProxy()
        assert "http_user" in proxy.user_dict
        assert "fast_http_user" in proxy.user_dict
        assert isinstance(proxy.user_dict["http_user"], ProxyHTTPUser)
        assert isinstance(proxy.user_dict["fast_http_user"], ProxyFastHTTPUser)

    def test_get_user(self):
        proxy = LocustUserProxy()
        assert isinstance(proxy.get_user("http_user"), ProxyHTTPUser)
        assert proxy.get_user("nonexistent") is None

    def test_set_user(self):
        proxy = LocustUserProxy()
        new_user = ProxyHTTPUser()
        proxy.set_user("custom", new_user)
        assert proxy.get_user("custom") is new_user

from typing import Dict, Any
from je_load_density.wrapper.proxy.user.fast_http_user_proxy import ProxyFastHTTPUser
from je_load_density.wrapper.proxy.user.http_user_proxy import ProxyHTTPUser


class LocustUserProxy:
    """
    Locust 使用者代理容器
    Locust User Proxy Container

    用來保存並管理 FastHTTPUser 與 HTTPUser 的代理。
    Used to store and manage FastHTTPUser and HTTPUser proxies.
    """

    def __init__(self) -> None:
        # 使用者代理字典 (User proxy dictionary)
        self.user_dict: Dict[str, Any] = {
            "fast_http_user": ProxyFastHTTPUser(),
            "http_user": ProxyHTTPUser(),
        }

    def get_user(self, user_type: str) -> Any:
        """
        取得指定類型的使用者代理
        Get specified user proxy

        :param user_type: "fast_http_user" 或 "http_user"
        :return: 對應的使用者代理 (Corresponding user proxy)
        """
        return self.user_dict.get(user_type)

    def set_user(self, user_type: str, user_instance: Any) -> None:
        """
        設定或替換使用者代理
        Set or replace user proxy

        :param user_type: 使用者類型 (User type key)
        :param user_instance: 使用者代理實例 (User proxy instance)
        """
        self.user_dict[user_type] = user_instance


# 建立全域代理容器實例
# Create global proxy container instance
locust_wrapper_proxy = LocustUserProxy()
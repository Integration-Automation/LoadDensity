from typing import Dict, Any, Optional
from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.wrapper.create_locust_env.create_locust_env import prepare_env
from je_load_density.wrapper.user_template.fast_http_user_template import FastHttpUserWrapper, set_wrapper_fasthttp_user
from je_load_density.wrapper.user_template.http_user_template import HttpUserWrapper, set_wrapper_http_user


def start_test(
    user_detail_dict: Dict[str, Any],
    user_count: int = 50,
    spawn_rate: int = 10,
    test_time: Optional[int] = 60,
    web_ui_dict: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    啟動壓力測試
    Start load test

    :param user_detail_dict: 使用者設定字典 (User detail dictionary)
    :param user_count: 使用者數量 (Number of users to spawn)
    :param spawn_rate: 每秒生成使用者數量 (Spawn rate per second)
    :param test_time: 測試持續時間 (Test duration in seconds)
    :param web_ui_dict: Web UI 設定，例如 {"host": "127.0.0.1", "port": 8089}
    :param kwargs: 其他參數 (extra parameters)
    :return: 測試設定摘要字典 (Summary dictionary of test configuration)
    """
    load_density_logger.info(
        f"start_test, user_detail_dict={user_detail_dict}, user_count={user_count}, "
        f"spawn_rate={spawn_rate}, test_time={test_time}, web_ui_dict={web_ui_dict}, params={kwargs}"
    )

    # 使用者類型映射 (User type mapping)
    user_dict = {
        "fast_http_user": {"actually_user": FastHttpUserWrapper, "init": set_wrapper_fasthttp_user},
        "http_user": {"actually_user": HttpUserWrapper, "init": set_wrapper_http_user},
    }

    user_type = user_detail_dict.get("user", "fast_http_user")
    user = user_dict.get(user_type)

    if user is None:
        raise ValueError(f"Unsupported user type: {user_type}")

    actually_user = user["actually_user"]
    init_function = user["init"]

    # 初始化使用者設定 (Initialize user configuration)
    init_function(user_detail_dict, **kwargs)

    # 建立並執行測試環境 (Create and run test environment)
    prepare_env(
        user_class=actually_user,
        user_count=user_count,
        spawn_rate=spawn_rate,
        test_time=test_time,
        web_ui_dict=web_ui_dict,
        **kwargs
    )

    # 回傳結構化結果 (Return structured result)
    return {
        "user_detail": user_detail_dict,
        "user_count": user_count,
        "spawn_rate": spawn_rate,
        "test_time": test_time,
        "web_ui": web_ui_dict,
    }
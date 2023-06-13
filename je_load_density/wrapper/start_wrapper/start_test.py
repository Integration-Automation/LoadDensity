from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.wrapper.create_locust_env.create_locust_env import prepare_env
from je_load_density.wrapper.user_template.fast_http_user_template import FastHttpUserWrapper, set_wrapper_fasthttp_user
from je_load_density.wrapper.user_template.http_user_template import HttpUserWrapper, set_wrapper_http_user


def start_test(
        user_detail_dict: dict,
        user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
        web_ui_dict: dict = None,
        **kwargs
):
    """
    :param user_detail_dict: dict use to create user
    :param user_count: how many user we want to spawn
    :param spawn_rate: one time will spawn how many user
    :param test_time: total test run time
    :param web_ui_dict: web ui dict include host and port like {"host": "127.0.0.1", "port": 8089}
    :param kwargs: to catch unknown param
    :return: None
    """
    load_density_logger.info(
        f"start_test, user_detail_dict: {user_detail_dict}, user_count: {user_count}, "
        f"spawn_rate: {spawn_rate}, test_time: {test_time}, web_ui_dict: {web_ui_dict}, "
        f"params: {kwargs}"
    )
    user_dict = {
        "fast_http_user": {"actually_user": FastHttpUserWrapper, "init": set_wrapper_fasthttp_user},
        "http_user": {"actually_user": HttpUserWrapper, "init": set_wrapper_http_user}
    }
    user = user_dict.get(user_detail_dict.get("user", "fast_http_user"))
    actually_user = user.get("actually_user", "actually_user")
    init_function = user.get("init", "init")
    init_function(user_detail_dict, **kwargs)

    prepare_env(
        user_class=actually_user, user_count=user_count, spawn_rate=spawn_rate, test_time=test_time,
        web_ui_dict=web_ui_dict, **kwargs
    )
    return str(user_detail_dict) + " " + "user_count: " + str(user_count) + " spawn_rate: " + str(
        spawn_rate) + " test_time: " + str(test_time)

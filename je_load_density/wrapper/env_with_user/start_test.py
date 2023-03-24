from je_load_density.wrapper.locust_as_library.locust_as_library import prepare_env
from je_load_density.wrapper.locust_template.http_user_with_requests import create_loading_test_user


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
    user = create_loading_test_user(user_detail_dict)
    prepare_env(
        user_class=user, user_count=user_count, spawn_rate=spawn_rate, test_time=test_time,
        web_ui_dict=web_ui_dict, **kwargs
    )
    return str(user_detail_dict) + " " + "user_count: " + str(user_count) + " spawn_rate: " + str(
        spawn_rate) + " test_time: " + str(test_time)

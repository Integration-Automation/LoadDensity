from je_load_density.wrapper.locust_template.http_user_with_api_testka import create_loading_test_user
from je_load_density.wrapper.locust_as_library.locust_as_library import start_test


def loading_test_with_user(
        user_detail_dict: dict,
        user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
        web_ui_dict: dict = None,
        **kwargs
):
    user = create_loading_test_user(user_detail_dict)
    start_test(
        user, user_count, spawn_rate, test_time,
        web_ui_dict, **kwargs
    )

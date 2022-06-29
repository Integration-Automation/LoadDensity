import sys

from locust import HttpUser
from locust import task
from locust.clients import HttpSession

from je_load_density.utils.get_data_strcture.get_api_data import get_api_response_data
from je_load_density.utils.exception.exception import LoadDensityAssertException

loading_test_detail_dict = dict()
record_list = list()


def create_loading_test_user(user_detail_dict: dict, **kwargs):
    """
    another_test_setting_dict are optional
    :param user_detail_dict: detail_dict should be included host http_method test_path
    """
    http_method = user_detail_dict.get("request_method", "get")
    request_url = user_detail_dict.get("request_url", "http://localhost")
    another_test_setting_dict = user_detail_dict.get("another_test_setting_dict", dict())
    assert_result_dict = user_detail_dict.get("assert_result_dict", None)
    loading_test_detail_dict.update(
        {
            "http_method": http_method,
            "request_url": request_url,
            "another_test_setting_dict": another_test_setting_dict,
            "assert_result_dict": assert_result_dict
        }
    )
    return HttpUserWrapper


def http_method_and_assert(with_httpsession: [
    HttpSession.get, HttpSession.head, HttpSession.put, HttpSession.post,
    HttpSession.patch, HttpSession.options, HttpSession.delete
], assert_result_dict: dict):
    """
    :param with_httpsession: use to get locust httpsession data
    :param assert_result_dict: use to assert data
    :return:
    """
    with with_httpsession(
            loading_test_detail_dict.get("request_url"),
            catch_response=True,
            **loading_test_detail_dict.get("another_test_setting_dict"),
    ) as response:
        response_data = get_api_response_data(response, None, None)
        for key, value in assert_result_dict.items():
            if response_data.get(key) != value:
                raise LoadDensityAssertException(
                    "value should be {right_value} but value was {wrong_value}".format(
                        right_value=value, wrong_value=response_data.get(key)
                    )
                )


class HttpUserWrapper(HttpUser):
    """
    locust httpuser use to test
    """
    host = ""
    min_wait = 5
    max_wait = 20


    def on_start(self):
        self.__http_method_dict = {
            "get": self.client.get,
            "put": self.client.put,
            "delete": self.client.delete,
            "post": self.client.post,
            "head": self.client.head,
            "options": self.client.options,
            "patch": self.client.patch,
        }
        self.__loading_test_detail_dict = loading_test_detail_dict
        self.__test_client = self.__http_method_dict.get(self.__loading_test_detail_dict.get("http_method"))

    @task
    def task_with_api_testka(self):
        try:
            another_test_setting_dict: dict = self.__loading_test_detail_dict.get("another_test_setting_dict")
            assert_result_dict: dict = self.__loading_test_detail_dict.get("assert_result_dict")
            if another_test_setting_dict is not None:
                if assert_result_dict is None:
                    self.__test_client(
                        self.__loading_test_detail_dict.get("request_url"),
                        **self.__loading_test_detail_dict.get("another_test_setting_dict")
                    )
                else:
                    http_method_and_assert(self.__test_client, assert_result_dict)

            else:
                if assert_result_dict is None:
                    self.__test_client(self.__loading_test_detail_dict.get("request_url"))
                else:
                    http_method_and_assert(self.__test_client, assert_result_dict)
        except Exception as error:
            print(repr(error), file=sys.stderr)

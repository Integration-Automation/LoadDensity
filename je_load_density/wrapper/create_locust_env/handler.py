from locust import events

from je_load_density.utils.test_record.test_record_class import test_record_instance


@events.request.add_listener
def handle_request(request_type, name, response_time, response_length, response,
                   context, exception, start_time, url, **kwargs):
    """
    handle every request event to record data
    :param request_type: default request event value
    :param name: default request event value
    :param response_time: default request event value
    :param response_length: default request event value
    :param response: default request event value
    :param context: default request event value
    :param exception: default request event value
    :param start_time: default request event value
    :param url: default request event value
    :param kwargs: catch some unknown param
    :return: None
    """
    if exception:
        test_record_instance.error_record_list.append(
            {
                "Method": request_type,
                "test_url": url,
                "name": name,
                "status_code": response.status_code,
                "error": exception
            }
        )
    else:
        test_record_instance.test_record_list.append(
            {
                "Method": request_type,
                "test_url": url,
                "name": name,
                "status_code": response.status_code,
                "text": str(response.text),
                "content": str(response.content),
                "headers": str(response.headers),
            }
        )

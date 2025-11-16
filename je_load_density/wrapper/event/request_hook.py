from je_load_density.utils.test_record.test_record_class import test_record_instance
from locust import events


@events.request.add_listener
def request_hook(
    start_time,
    url,
    request_type,
    name,
    context,
    response,
    exception,
    response_length,
    response_time,
    **kwargs
):
    """
    Locust request hook
    將每個 request 的結果紀錄到 test_record_instance
    """

    if exception is None:
        # 成功紀錄 (Success record)
        test_record_instance.test_record_list.append(
            {
                "Method": str(request_type),
                "test_url": str(url),
                "name": str(name),
                "status_code": str(response.status_code),
                "text": str(response.text),
                "content": str(response.content),
                "headers": str(response.headers),
                "error": None,  # 成功時 error 為 None
            }
        )
    else:
        # 失敗紀錄 (Failure record)
        test_record_instance.error_record_list.append(
            {
                "Method": str(request_type),
                "test_url": str(url),
                "name": str(name),
                "status_code": str(response.status_code) if response else None,
                "text": str(response.text) if response else None,
                "error": str(exception),  # 失敗時紀錄 exception
            }
        )
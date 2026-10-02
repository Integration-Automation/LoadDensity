from locust import events

from je_load_density.utils.test_record.contract import from_legacy_record, record_request
from je_load_density.utils.test_record.test_record_class import test_record_instance


def _epoch_seconds(start_time):
    """
    Locust 傳入的請求開始時間（epoch 秒），沒有就回傳 None
    The request's start time from Locust (epoch seconds), or None when absent.

    Successes and failures are kept in two lists, so this is the only way a report can put them
    back in the order the requests were made (service map edges, Allure start/stop).
    """
    return float(start_time) if start_time is not None else None


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
                "status_code": str(response.status_code) if response is not None else None,
                "text": str(response.text) if response is not None else None,
                "content": str(response.content) if response is not None else None,
                "headers": str(response.headers) if response is not None else None,
                "response_time_ms": float(response_time or 0),
                "response_length": int(response_length or 0),
                "error": None,
                "start_time": _epoch_seconds(start_time),
            }
        )
    else:
        # 失敗紀錄 (Failure record)
        test_record_instance.error_record_list.append(
            {
                "Method": str(request_type),
                "test_url": str(url),
                "name": str(name),
                "status_code": str(response.status_code) if response is not None else None,
                "text": str(response.text) if response is not None else None,
                "response_time_ms": float(response_time or 0),
                "response_length": int(response_length or 0),
                "error": str(exception),
                "start_time": _epoch_seconds(start_time),
            }
        )

    outcome = "passed" if exception is None else "failed"
    records = test_record_instance.test_record_list if exception is None else test_record_instance.error_record_list
    entry = records[-1]
    selected_run = kwargs.get("record_run")
    if selected_run is not None:
        from_legacy_record(entry, selected_run, outcome)
    else:
        record_request(entry, outcome)

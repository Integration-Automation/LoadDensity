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


def _response_fields(response, successful: bool) -> dict[str, object]:
    """Preserve response metadata, including HTTP error responses whose truth value is false."""
    if response is None:
        fields = {"status_code": None, "text": None}
        if successful:
            fields.update(content=None, headers=None)
        return fields
    fields = {"status_code": str(response.status_code), "text": str(response.text)}
    if successful:
        fields.update(content=str(response.content), headers=str(response.headers))
    return fields


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

    successful = exception is None
    entry = {"Method": str(request_type), "test_url": str(url), "name": str(name)}
    entry.update(_response_fields(response, successful))
    entry.update(response_time_ms=float(response_time or 0), response_length=int(response_length or 0),
                 error=None if successful else str(exception), start_time=_epoch_seconds(start_time))
    outcome = "passed" if successful else "failed"
    sink = kwargs.get("record_sink")
    if sink is not None:
        sink.capture_legacy(entry, outcome)
        return
    records = test_record_instance.test_record_list if successful else test_record_instance.error_record_list
    records.append(entry)
    selected_run = kwargs.get("record_run")
    if selected_run is not None:
        from_legacy_record(entry, selected_run, outcome)
    else:
        record_request(entry, outcome)

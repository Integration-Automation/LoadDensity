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
    if exception is None:
        test_record_instance.test_record_list.append(
            {
                "Method": str(request_type),
                "test_url": str(url),
                "name": str(name),
                "text": str(response.text),
                "content": str(response.content),
                "headers": str(response.headers),
                "status_code": str(response.status_code),
                "error": str(exception)
            }
        )
    else:
        test_record_instance.error_record_list.append(
            {
                "Method": str(request_type),
                "test_url": str(url),
                "name": str(name),
                "status_code": str(response.status_code),
                "text": str(response.text)
            }
        )

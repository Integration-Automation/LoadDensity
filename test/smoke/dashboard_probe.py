"""Exercise real dashboard JSON and SSE endpoints, then close the listening server."""

from je_load_density.utils.dashboard.live_dashboard import start_dashboard, stop_dashboard
from je_load_density.utils.test_record.test_record_class import test_record_instance


def main() -> None:
    """Check dashboard transport and data against a measured request fixture."""
    import json
    from urllib.request import urlopen

    test_record_instance.clear_records()
    test_record_instance.test_record_list.append({
        "Method": "GET", "test_url": "http://localhost/ok", "name": "health",
        "status_code": "200", "response_time_ms": 25, "response_length": 2,
    })
    dashboard = start_dashboard(port=0, refresh_seconds=0.01)
    try:
        address = f"http://127.0.0.1:{dashboard._httpd.server_port}"
        with urlopen(address + "/snapshot", timeout=5) as response:
            snapshot = json.load(response)
        with urlopen(address + "/events", timeout=5) as response:
            content_type = response.headers["Content-Type"]
            event = response.readline().decode("utf-8")
        print(json.dumps({"snapshot": snapshot, "content_type": content_type,
                          "event": json.loads(event.removeprefix("data: "))}))
    finally:
        stop_dashboard()


if __name__ == "__main__":
    main()

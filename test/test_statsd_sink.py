import socket
import threading

from je_load_density.utils.metrics.statsd_sink import (
    format_packets,
    start_statsd_sink,
    stop_statsd_sink,
)


def test_format_packets_emits_counter_latency_size_with_tags():
    packets = format_packets("loaddensity", "GET", "/x",
                              response_time_ms=42.0, response_length=1024,
                              outcome="success")
    assert packets[0] == "loaddensity.requests:1|c|#method:GET,name:/x,outcome:success"
    assert packets[1].startswith("loaddensity.request.latency:42|ms")
    assert packets[2].startswith("loaddensity.response.size:1024|h")


def test_format_packets_sanitizes_tag_values():
    packets = format_packets("loaddensity", "POST", "name|with,bad:chars",
                              response_time_ms=None, response_length=None,
                              outcome="success")
    tags_segment = packets[0].split("#", 1)[1]
    assert "|" not in tags_segment
    assert "," not in tags_segment.replace("method:POST,name:", "").split(",")[0]
    assert "name_with_bad_chars" in tags_segment


def test_format_packets_omits_latency_and_size_when_none():
    packets = format_packets("loaddensity", "GET", "/x",
                              response_time_ms=None, response_length=None,
                              outcome="success")
    assert len(packets) == 1


def test_start_statsd_sink_returns_emitter_then_stop_clears():
    emitter = start_statsd_sink(host="127.0.0.1", port=8125, prefix="x")
    try:
        assert emitter.prefix == "x"
    finally:
        stop_statsd_sink()


def test_statsd_sink_emits_to_udp_listener():
    received: list = []
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    stop_event = threading.Event()

    def _run():
        server.settimeout(0.1)
        while not stop_event.is_set():
            try:
                data, _ = server.recvfrom(2048)
                received.append(data.decode("utf-8"))
            except socket.timeout:
                continue

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    try:
        emitter = start_statsd_sink(host="127.0.0.1", port=port, prefix="ld")
        emitter.emit("ld.requests:1|c|#x")
        # poll briefly
        for _ in range(20):
            if received:
                break
            threading.Event().wait(0.05)
        assert received
        assert received[0].startswith("ld.requests:")
    finally:
        stop_statsd_sink()
        stop_event.set()
        thread.join(timeout=1)
        server.close()

from je_load_density.wrapper.user_template.grpc_user_template import (
    _build_request_iter,
    _drain_stream,
    _invoke_rpc,
    _response_bytes,
)


class _FakeRequest:
    def __init__(self, **fields):
        self.fields = fields

    def ByteSize(self) -> int:  # NOSONAR mirror protobuf method name
        return 8


def test_response_bytes_with_bytesize():
    assert _response_bytes(_FakeRequest()) == 8


def test_response_bytes_with_none():
    assert _response_bytes(None) == 0


def test_drain_stream_sums_bytes():
    iterator = iter([_FakeRequest(), _FakeRequest(), _FakeRequest()])
    assert _drain_stream(iterator) == 24


def test_build_request_iter_handles_list_and_single():
    requests = list(_build_request_iter(_FakeRequest, [{"x": 1}, {"y": 2}]))
    assert [r.fields for r in requests] == [{"x": 1}, {"y": 2}]
    requests = list(_build_request_iter(_FakeRequest, {"x": 1}))
    assert requests[0].fields == {"x": 1}


def test_invoke_rpc_unary_returns_response_bytes():
    calls = []

    def rpc(request, timeout, metadata):
        calls.append((request, timeout, metadata))
        return _FakeRequest()

    length = _invoke_rpc(rpc, _FakeRequest, {"x": 1}, (), 5.0, "unary")
    assert length == 8
    assert len(calls) == 1


def test_invoke_rpc_server_stream_drains_iterator():
    def rpc(request, timeout, metadata):
        yield _FakeRequest()
        yield _FakeRequest()

    assert _invoke_rpc(rpc, _FakeRequest, {}, (), 5.0, "server_stream") == 16


def test_invoke_rpc_client_stream_sends_iterator():
    seen = []

    def rpc(iterator, timeout, metadata):
        seen.extend(list(iterator))
        return _FakeRequest()

    length = _invoke_rpc(rpc, _FakeRequest, [{"a": 1}, {"b": 2}],
                          (), 5.0, "client_stream")
    assert length == 8
    assert len(seen) == 2


def test_invoke_rpc_bidi_drains_response_stream():
    def rpc(iterator, timeout, metadata):
        for _ in iterator:
            yield _FakeRequest()

    length = _invoke_rpc(rpc, _FakeRequest, [{"a": 1}, {"b": 2}],
                          (), 5.0, "bidi")
    assert length == 16

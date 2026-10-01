"""
The socket server's wire replies, byte for byte.

Each case feeds one request to a connection handler and compares everything the server writes back.
``_exchange`` is the only part that knows how the server is built, so the expectations survive a change of
implementation.
"""
import json
import struct

import pytest

from je_load_density.utils.executor.action_executor import add_command_to_executor
from je_load_density.utils.socket_server.load_density_socket_server import TCPServer

END = b"Return_Data_Over_JE\n"
TOKEN = "s3cret"
_FRAME = struct.Struct("!I")


def _echo_for_socket_test(value):
    return value


add_command_to_executor({"socket_test_echo": _echo_for_socket_test})


class _FakeConnection:
    """Hands out the request (at most ``size`` bytes per ``recv``, as a socket does), records everything sent."""

    def __init__(self, request: bytes) -> None:
        self._pending = bytearray(request)
        self.sent = bytearray()

    def recv(self, size: int) -> bytes:
        chunk = bytes(self._pending[:size])
        del self._pending[:size]
        return chunk

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def close(self) -> None:
        """The handler closes the connection when it is done."""


def _frame(body: bytes) -> bytes:
    return _FRAME.pack(len(body)) + body


def _exchange(request: bytes, framed: bool = False, token=None):
    server = TCPServer(framed=framed, token=token)
    try:
        connection = _FakeConnection(request)
        server.handle(connection)
        return bytes(connection.sent), server.close_flag
    finally:
        server.server.close()


def _echo(value: str) -> bytes:
    return json.dumps([["socket_test_echo", {"value": value}]]).encode()


def test_runs_actions_and_replies_one_line_per_record():
    assert _exchange(_echo("hi")) == (b"hi\n" + END, False)


def test_bad_json_replies_the_error_then_the_marker():
    reply, _ = _exchange(b"not json")
    assert reply == b"Error: Expecting value: line 1 column 1 (char 0)\n" + END


def test_a_failing_action_is_a_record_line():
    reply, _ = _exchange(b'[["no_such_command_xyz"]]')
    assert reply.endswith(b"\n" + END)
    assert b"no_such_command_xyz" in reply


def test_empty_request_gets_no_reply():
    assert _exchange(b"") == (b"", False)


def test_quit_without_a_token_stops_the_server():
    assert _exchange(b"quit_server") == (b"Server shutting down\n", True)


def test_quit_with_a_token_needs_the_envelope():
    assert _exchange(b"quit_server", token=TOKEN) == (b"Error: token required\n", False)


def test_a_token_refuses_a_bare_action_list():
    assert _exchange(_echo("hi"), token=TOKEN) == (b"Error: token required\n", False)


def test_envelope_with_the_token_runs_the_command():
    request = json.dumps({"token": TOKEN, "command": [["socket_test_echo", {"value": "ok"}]]}).encode()
    assert _exchange(request, token=TOKEN) == (b"ok\n" + END, False)


def test_envelope_with_a_wrong_token_is_refused():
    request = json.dumps({"token": "wrong", "command": [["socket_test_echo", {"value": "x"}]]}).encode()
    assert _exchange(request, token=TOKEN) == (b"Error: unauthorised\n", False)


def test_envelope_quit_with_the_token_stops_the_server():
    request = json.dumps({"token": TOKEN, "op": "quit"}).encode()
    assert _exchange(request, token=TOKEN) == (b"Server shutting down\n", True)


def test_envelope_without_a_command_replies_only_the_marker():
    request = json.dumps({"token": TOKEN}).encode()
    assert _exchange(request, token=TOKEN) == (END, False)


def test_envelope_works_without_a_configured_token():
    request = json.dumps({"command": [["socket_test_echo", {"value": "plain"}]]}).encode()
    assert _exchange(request) == (b"plain\n" + END, False)


def test_framed_request_gets_one_frame_per_line():
    assert _exchange(_frame(_echo("hi")), framed=True) == (_frame(b"hi\n") + _frame(END), False)


@pytest.mark.parametrize("header", [_FRAME.pack(0), _FRAME.pack((1 << 20) + 1)])
def test_framed_request_with_a_bad_length_gets_no_reply(header):
    assert _exchange(header, framed=True) == (b"", False)

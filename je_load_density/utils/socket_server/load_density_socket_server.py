import hmac
import json
import os
import ssl
import struct
import sys
from socket import AF_INET, SOCK_STREAM
from typing import Any, Optional

import gevent
from gevent import monkey
from gevent import socket

from je_load_density.utils.executor.action_executor import execute_action

_MAX_PAYLOAD_BYTES = 1 << 20  # 1 MiB
_FRAME_HEADER = struct.Struct("!I")


class TCPServer:
    """
    基於 gevent 的 TCP 伺服器
    TCP server based on gevent.

    Modes:
        legacy   - single recv up to 8 KiB, raw JSON line, no auth
        framed   - 4-byte big-endian length prefix + JSON body
        framed+tls - wrap socket with TLS (cert/key required)

    Auth:
        Optional shared secret token compared via hmac. Required to
        execute privileged commands (quit_server) and any payload
        once a token is configured.
    """

    def __init__(
        self,
        framed: bool = False,
        token: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
    ) -> None:
        self.close_flag: bool = False
        self.framed: bool = framed
        self.token: Optional[str] = token
        self.certfile = certfile
        self.keyfile = keyfile
        self.server: socket.socket = socket.socket(AF_INET, SOCK_STREAM)
        self._tls_context: Optional[ssl.SSLContext] = None
        if certfile and keyfile:
            self._tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self._tls_context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    def socket_server(self, host: str, port: int) -> None:
        self.server.bind((host, port))
        self.server.listen()
        print(f"Server started on {host}:{port}", flush=True)

        while not self.close_flag:
            try:
                connection, _ = self.server.accept()
                if self._tls_context is not None:
                    try:
                        connection = self._tls_context.wrap_socket(connection, server_side=True)
                    except ssl.SSLError as error:
                        print(f"TLS handshake failed: {error}", file=sys.stderr)
                        connection.close()
                        continue
                gevent.spawn(self.handle, connection)
            except Exception as error:
                print(f"Server error: {error}", file=sys.stderr)
                break

        self.server.close()
        print("Server shutdown complete", flush=True)

    def _read_frame(self, connection) -> Optional[bytes]:
        if not self.framed:
            data = connection.recv(8192)
            return data or None
        header = self._read_exact(connection, _FRAME_HEADER.size)
        if header is None:
            return None
        (length,) = _FRAME_HEADER.unpack(header)
        if length == 0 or length > _MAX_PAYLOAD_BYTES:
            return None
        return self._read_exact(connection, length)

    @staticmethod
    def _read_exact(connection, size: int) -> Optional[bytes]:
        buffer = bytearray()
        while len(buffer) < size:
            chunk = connection.recv(size - len(buffer))
            if not chunk:
                return None
            buffer.extend(chunk)
        return bytes(buffer)

    def _send_frame(self, connection, payload: bytes) -> None:
        if self.framed:
            connection.sendall(_FRAME_HEADER.pack(len(payload)) + payload)
        else:
            connection.sendall(payload)

    def _check_token(self, supplied: Any) -> bool:
        if self.token is None:
            return True
        if not isinstance(supplied, str):
            return False
        return hmac.compare_digest(self.token, supplied)

    def handle(self, connection) -> None:
        try:
            raw = self._read_frame(connection)
            if not raw:
                return

            command_string = raw.strip().decode("utf-8", errors="replace")
            print(f"Command received: {len(command_string)} bytes", flush=True)

            if command_string == "quit_server":
                if self.token is not None:
                    self._send_frame(connection, b"Error: token required\n")
                    return
                self.close_flag = True
                self._send_frame(connection, b"Server shutting down\n")
                print("Now quit server", flush=True)
                return

            try:
                payload = json.loads(command_string)
            except json.JSONDecodeError as error:
                self._send_frame(connection, f"Error: {error}\n".encode("utf-8"))
                self._send_frame(connection, b"Return_Data_Over_JE\n")
                return

            command = payload
            if isinstance(payload, dict) and ("token" in payload or "command" in payload):
                if not self._check_token(payload.get("token")):
                    self._send_frame(connection, b"Error: unauthorised\n")
                    return
                command = payload.get("command")
                if payload.get("op") == "quit":
                    self.close_flag = True
                    self._send_frame(connection, b"Server shutting down\n")
                    return
            elif self.token is not None:
                self._send_frame(connection, b"Error: token required\n")
                return

            if command is None:
                self._send_frame(connection, b"Return_Data_Over_JE\n")
                return

            try:
                for execute_return in execute_action(command).values():
                    self._send_frame(connection, f"{execute_return}\n".encode("utf-8"))
                self._send_frame(connection, b"Return_Data_Over_JE\n")
            except Exception as error:
                self._send_frame(connection, f"Error: {error}\n".encode("utf-8"))
                self._send_frame(connection, b"Return_Data_Over_JE\n")
        finally:
            connection.close()


def start_load_density_socket_server(
    host: str = "localhost",
    port: int = 9940,
    framed: bool = False,
    token: Optional[str] = None,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
) -> TCPServer:
    """
    啟動 LoadDensity TCP 伺服器
    Start LoadDensity TCP server.

    The token may also come from the LOAD_DENSITY_SOCKET_TOKEN
    environment variable so secrets are not embedded in callers.
    """
    monkey.patch_all()
    if token is None:
        token = os.environ.get("LOAD_DENSITY_SOCKET_TOKEN")
    server = TCPServer(framed=framed, token=token, certfile=certfile, keyfile=keyfile)
    server.socket_server(host, port)
    return server

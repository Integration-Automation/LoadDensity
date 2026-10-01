"""
LoadDensity's TCP control server (port 9940): je_action_core's action server in LoadDensity's dialect.

- Requests are raw (one 8 KiB ``recv``) or, with ``framed=True``, 4-byte big-endian length-prefixed; every reply
  line is then its own frame.
- With a token (argument or ``LOAD_DENSITY_SOCKET_TOKEN``), only ``{"token": ..., "command": [...]}`` runs and
  ``{"token": ..., "op": "quit"}`` stops the server. Tokens are compared in constant time.
- ``certfile`` and ``keyfile`` wrap every connection in TLS 1.2 or later.
- Replies: one line per record, then ``Return_Data_Over_JE``; failures are ``Error: <text>``. The log line names
  only the request's size, never its text (it may hold the token).
"""
import os
import sys
from typing import Optional

from gevent import monkey
from je_action_core import (
    ActionTCPServer,
    EnvelopeTokenRequestHandler,
    Framing,
    ReplyMessages,
    SocketServerSettings,
    server_tls_context,
    start_action_socket_server,
)

from je_load_density.utils.executor.action_executor import execute_action

TOKEN_ENVIRONMENT_VARIABLE = "LOAD_DENSITY_SOCKET_TOKEN"  # noqa: S105 - a variable name, not a value
_MESSAGES = ReplyMessages(
    record="{value}",
    error="Error: {error}",
    quit="Server shutting down",
    auth_required="Error: token required",
    auth_refused="Error: unauthorised",
    log_command="Command received: {size} bytes",
)


def _print_info(message: str) -> None:
    print(message, flush=True)


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def socket_server_settings(
    framed: bool = False,
    token: Optional[str] = None,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
) -> SocketServerSettings:
    """
    LoadDensity 伺服器的設定
    The server settings for LoadDensity's dialect (see the module docstring).
    """
    return SocketServerSettings(
        execute=execute_action,
        framing=Framing.LENGTH_PREFIX if framed else Framing.RAW,
        decode_errors="replace",
        messages=_MESSAGES,
        secret=token,
        tls_context=server_tls_context(certfile, keyfile) if certfile and keyfile else None,
        log_info=_print_info,
        log_error=_print_error,
    )


def start_load_density_socket_server(
    host: str = "localhost",
    port: int = 9940,
    framed: bool = False,
    token: Optional[str] = None,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
) -> ActionTCPServer:
    """
    啟動 LoadDensity TCP 伺服器
    Start LoadDensity's TCP server and block until a client stops it, then return the stopped server.

    gevent patches the standard library first (``monkey.patch_all()``), so connections run on greenlets.
    The token may also come from the ``LOAD_DENSITY_SOCKET_TOKEN`` environment variable so secrets are not
    embedded in callers.
    """
    monkey.patch_all()
    if token is None:
        token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE)
    settings = socket_server_settings(framed=framed, token=token, certfile=certfile, keyfile=keyfile)
    server = start_action_socket_server(host, port, settings, EnvelopeTokenRequestHandler)
    print(f"Server started on {host}:{port}", flush=True)
    server.close_event.wait()
    server.shutdown()
    server.server_close()
    print("Server shutdown complete", flush=True)
    return server

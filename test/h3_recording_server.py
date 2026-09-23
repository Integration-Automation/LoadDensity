"""
HTTP/3 server for ``test_http3_user_template.py``, run as its own process.

It runs in a separate process because importing ``je_load_density`` loads Locust, and Locust's
gevent patching turns threads into greenlets; a thread running an asyncio loop would then block
the test. Usage: ``python h3_recording_server.py CERT KEY LOG``. The process prints its UDP port
on the first stdout line, then serves until killed. Every request is appended to LOG as one JSON
line holding the headers and the hex-encoded body. The reply has the status named in the
``x-status`` request header (default 200) and the body ``h3:<method>:<request body>``.
"""

import asyncio
import json
import sys
from functools import partial

from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration


class RecordingH3Server(QuicConnectionProtocol):
    """Answers each request stream once it has ended, and logs the request."""

    def __init__(self, *args, log_path, **kwargs):
        super().__init__(*args, **kwargs)
        self._http = H3Connection(self._quic)
        self._log_path = log_path
        self._streams = {}

    def quic_event_received(self, event):
        for h3_event in self._http.handle_event(event):
            if isinstance(h3_event, HeadersReceived):
                self._streams[h3_event.stream_id] = (dict(h3_event.headers), bytearray())
            elif isinstance(h3_event, DataReceived):
                self._streams[h3_event.stream_id][1].extend(h3_event.data)
            else:
                continue
            if h3_event.stream_ended:
                self._answer(h3_event.stream_id)

    def _answer(self, stream_id):
        headers, body = self._streams.pop(stream_id)
        record = {
            "headers": {name.decode(): value.decode() for name, value in headers.items()},
            "body": bytes(body).hex(),
        }
        with open(self._log_path, "a", encoding="utf-8") as log:
            log.write(json.dumps(record) + "\n")
        reply = b"h3:" + headers[b":method"] + b":" + bytes(body)
        status = headers.get(b"x-status", b"200")
        self._http.send_headers(stream_id, [(b":status", status), (b"content-length", str(len(reply)).encode())])
        self._http.send_data(stream_id, reply, end_stream=True)
        self.transmit()


async def main(cert_path, key_path, log_path):
    configuration = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    configuration.load_cert_chain(cert_path, key_path)
    server = await serve(
        "127.0.0.1", 0, configuration=configuration, create_protocol=partial(RecordingH3Server, log_path=log_path),
    )
    print(server._transport.get_extra_info("sockname")[1], flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:4]))

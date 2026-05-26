Auth
====

Overview
--------

Three auth helpers cover the most common load-test authentication
patterns without pulling in heavy SDKs:

* OAuth2 client with token cache.
* JWT signer (HS256/384/512 + RS256/384/512 via ``cryptography`` soft-dep).
* AWS Signature v4 request signer (pure stdlib).

Plus mTLS client-cert support on every HTTP user template via
``task["cert"]``.

OAuth2
------

.. code-block:: python

    from je_load_density import (
        OAuth2Client,
        fetch_client_credentials_token,
        fetch_password_token,
        refresh_token,
    )

    client = OAuth2Client(
        token_url="https://idp/token",
        client_id="id", client_secret="secret",
        scope="read:x",
    )

    token = client.get_client_credentials()
    # Subsequent calls reuse the same token until expires_in elapses.

    token2 = client.get_password(username="alice", password="rotate-me")
    refreshed = client.refresh(refresh_token=token["refresh_token"])

    client.clear()  # forget cached tokens (e.g. after rotation)

Standalone helpers — ``fetch_client_credentials_token``,
``fetch_password_token``, ``refresh_token`` — accept a ``poster``
callable so tests can stub the network.

JWT
---

.. code-block:: python

    from je_load_density import sign_jwt, decode_jwt

    # HS256 — pure stdlib
    token = sign_jwt(
        {"sub": "alice", "role": "admin"},
        secret="topsecret",
        algorithm="HS256",
        expires_in_seconds=300,
    )

    header, payload, signature = decode_jwt(token)

    # RS256 — requires ``cryptography``
    with open("private.pem", "rb") as fh:
        pem = fh.read()
    rs_token = sign_jwt({"sub": "x"}, secret=pem, algorithm="RS256")

``decode_jwt`` does *not* verify the signature — it just splits and
base64-decodes the three segments. Use it for inspection or to feed
into your own verification step.

AWS SigV4
---------

.. code-block:: python

    from je_load_density import sign_aws_request

    headers = sign_aws_request(
        method="GET",
        url="https://s3.amazonaws.com/mybucket/key",
        region="us-east-1",
        service="s3",
        access_key="AKIDEXAMPLE",
        secret_key="…",
        session_token=None,    # set when using STS
    )
    # Pass the returned headers to your HTTP client.

mTLS
----

Add a ``cert`` field to any HTTP task; it is forwarded straight to
``requests`` / ``geventhttpclient``:

.. code-block:: json

    {"method": "get", "request_url": "https://mtls.api/x",
     "cert": ["/etc/ssl/client.pem", "/etc/ssl/key.pem"]}

A string value (combined PEM) and a 2-tuple (cert, key) are both
accepted. ``client_cert`` is recognised as an alias.

Auth API
========

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
        client_id="id",
        client_secret="secret",
        scope="read:x",
        timeout=5.0,
        safety_window=30.0,   # refresh `safety_window` seconds early
    )

    token = client.get_client_credentials()
    token = client.get_password(username="alice", password="rotate-me")
    token = client.refresh(refresh_token="r1")
    client.clear()

Each method returns the raw token dict. Repeated calls within the same
``expires_in`` window reuse the cached value.

Standalone helpers — ``fetch_client_credentials_token``,
``fetch_password_token``, ``refresh_token`` — accept a ``poster``
callable so tests can stub the network without monkey-patching
``urllib``.

JWT
---

.. code-block:: python

    from je_load_density import sign_jwt, decode_jwt

    token = sign_jwt(
        payload={"sub": "alice"},
        secret="topsecret",
        algorithm="HS256",       # HS384 / HS512 / RS256 / RS384 / RS512
        expires_in_seconds=300,
    )
    header, payload, signature = decode_jwt(token)

HS algorithms use stdlib ``hmac``; RS algorithms require
``cryptography`` (``[auth]`` extra). ``decode_jwt`` does not verify
the signature.

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
        body=b"",
        session_token=None,
    )

Returned dict carries ``Authorization`` + ``x-amz-date`` +
``x-amz-content-sha256`` (and ``x-amz-security-token`` when a session
token is set). Plug it into any HTTP user template.

mTLS
----

Add a ``cert`` field to any HTTP task; it is forwarded straight to the
underlying HTTP client. The ``client_cert`` alias is also accepted.

.. code-block:: json

    {"method": "get", "request_url": "https://mtls.api/x",
     "cert": ["/etc/ssl/client.pem", "/etc/ssl/key.pem"]}

Auth
====

概觀
----

三個 auth helper 覆蓋壓測最常見的認證情境,不引入肥大 SDK:

* OAuth2 client 含 token cache
* JWT 簽發(HS256/384/512 + RS256/384/512,RS 系列需 ``cryptography``)
* AWS Signature v4 簽章(純 stdlib)

加上所有 HTTP user template 透過 ``task["cert"]`` 即可走 mTLS。

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

    token = client.get_client_credentials()  # cache 至 expires_in 結束
    token2 = client.get_password(username="alice", password="rotate-me")
    refreshed = client.refresh(refresh_token=token["refresh_token"])

    client.clear()  # token rotation 後清快取

三個獨立 helper 都接受 ``poster=`` 注入,以便測試 stub 網路。

JWT
---

.. code-block:: python

    from je_load_density import sign_jwt, decode_jwt

    token = sign_jwt(
        {"sub": "alice", "role": "admin"},
        secret="topsecret", algorithm="HS256",
        expires_in_seconds=300,
    )
    header, payload, signature = decode_jwt(token)

    # RS256 需 cryptography
    with open("private.pem", "rb") as fh:
        pem = fh.read()
    rs_token = sign_jwt({"sub": "x"}, secret=pem, algorithm="RS256")

``decode_jwt`` 不驗簽,只切三段做 base64 解碼。要驗證可串接你的
verifier。

AWS SigV4
---------

.. code-block:: python

    from je_load_density import sign_aws_request

    headers = sign_aws_request(
        method="GET",
        url="https://s3.amazonaws.com/mybucket/key",
        region="us-east-1", service="s3",
        access_key="AKIDEXAMPLE", secret_key="...",
        session_token=None,    # 用 STS 時設定
    )

mTLS
----

在任何 HTTP task 加 ``cert``,會直接傳給 ``requests`` /
``geventhttpclient``:

.. code-block:: json

    {"method": "get", "request_url": "https://mtls.api/x",
     "cert": ["/etc/ssl/client.pem", "/etc/ssl/key.pem"]}

字串(合併 PEM)或 2-tuple(cert, key)皆可。``client_cert`` 為別名。

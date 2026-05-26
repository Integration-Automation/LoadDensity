import datetime
import time

import pytest

from je_load_density.utils.auth.aws_sigv4 import sign_aws_request
from je_load_density.utils.auth.jwt_signer import decode_jwt, sign_jwt
from je_load_density.utils.auth.oauth2 import (
    OAuth2Client,
    fetch_client_credentials_token,
)


# -------------------------------------------------------- OAuth2
def test_fetch_client_credentials_posts_form_with_basic_auth():
    seen = {}

    def poster(url, body, headers, timeout):
        seen["url"] = url
        seen["body"] = body
        seen["headers"] = headers
        return {"access_token": "tok", "token_type": "Bearer", "expires_in": 60}

    token = fetch_client_credentials_token(
        "https://idp/token", "id", "secret", scope="read:x",
        poster=poster,
    )
    assert token["access_token"] == "tok"
    assert seen["url"] == "https://idp/token"
    assert seen["headers"]["Authorization"].startswith("Basic ")
    assert b"grant_type=client_credentials" in seen["body"]
    assert b"scope=read%3Ax" in seen["body"]


def test_oauth2_client_caches_token_until_expiry():
    calls = []

    def poster(url, body, headers, timeout):
        calls.append(url)
        return {"access_token": f"t{len(calls)}", "expires_in": 3600}

    client = OAuth2Client(
        token_url="https://idp/token",
        client_id="id", client_secret="secret",
        poster=poster, safety_window=0,
    )
    assert client.get_client_credentials()["access_token"] == "t1"
    assert client.get_client_credentials()["access_token"] == "t1"
    assert len(calls) == 1

    client.clear()
    assert client.get_client_credentials()["access_token"] == "t2"


def test_oauth2_client_refresh_returns_new_token():
    def poster(url, body, headers, timeout):
        return {"access_token": "fresh", "refresh_token": "r2",
                "expires_in": 60}

    client = OAuth2Client(token_url="https://idp/token",
                          client_id="id", client_secret="secret",
                          poster=poster)
    new = client.refresh("r1")
    assert new["access_token"] == "fresh"


# -------------------------------------------------------- JWT
def test_sign_jwt_hs256_roundtrip():
    token = sign_jwt({"sub": "alice", "role": "admin"}, secret="topsecret",
                     algorithm="HS256")
    header, payload, signature = decode_jwt(token)
    assert header["alg"] == "HS256"
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
    assert len(signature) == 32


def test_sign_jwt_adds_exp_when_expires_in_seconds():
    before = int(time.time())
    token = sign_jwt({"sub": "x"}, secret="s", expires_in_seconds=120)
    _, payload, _ = decode_jwt(token)
    assert payload["exp"] >= before + 119


def test_sign_jwt_rejects_unknown_algorithm():
    with pytest.raises(ValueError):
        sign_jwt({"sub": "x"}, secret="s", algorithm="ZZ999")


def test_decode_jwt_rejects_malformed_token():
    with pytest.raises(ValueError):
        decode_jwt("a.b")


# -------------------------------------------------------- AWS SigV4
def test_sign_aws_request_attaches_authorization_and_date():
    when = datetime.datetime(2026, 5, 26, 12, 0, 0,
                              tzinfo=datetime.timezone.utc)
    headers = sign_aws_request(
        method="GET",
        url="https://s3.amazonaws.com/mybucket/file?prefix=a",
        region="us-east-1",
        service="s3",
        access_key="AKIDEXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
        now=when,
    )
    assert headers["x-amz-date"] == "20260526T120000Z"
    assert headers["x-amz-content-sha256"]
    auth = headers["Authorization"]
    assert auth.startswith("AWS4-HMAC-SHA256")
    assert "Credential=AKIDEXAMPLE/20260526/us-east-1/s3/aws4_request" in auth
    assert "SignedHeaders=" in auth
    assert "Signature=" in auth


def test_sign_aws_request_is_deterministic_for_same_inputs():
    when = datetime.datetime(2026, 5, 26, 12, 0, 0,
                              tzinfo=datetime.timezone.utc)
    args = {
        "method": "POST",
        "url": "https://ec2.us-west-2.amazonaws.com/?Action=DescribeInstances",
        "region": "us-west-2",
        "service": "ec2",
        "access_key": "AKIDEXAMPLE",
        "secret_key": "secret",
        "now": when,
        "body": "Action=DescribeInstances",
    }
    first = sign_aws_request(**args)
    second = sign_aws_request(**args)
    assert first["Authorization"] == second["Authorization"]


def test_sign_aws_request_includes_session_token_header():
    headers = sign_aws_request(
        method="GET", url="https://s3.amazonaws.com/bucket",
        region="us-east-1", service="s3",
        access_key="AK", secret_key="sk",
        session_token="SESSION",
    )
    assert headers["x-amz-security-token"] == "SESSION"

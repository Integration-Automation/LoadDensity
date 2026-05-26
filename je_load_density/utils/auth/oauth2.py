"""
OAuth2 token helpers with a tiny in-memory cache.

Three flows supported:

* client_credentials
* password (Resource Owner Password Credentials)
* refresh_token

Each helper returns the raw token dict; ``OAuth2Client`` wraps them with
a cache keyed on token-endpoint + scope, so subsequent calls reuse a
still-valid token instead of hitting the IdP on every task.

Network I/O is pluggable via the ``poster`` argument — tests inject a
fake poster.
"""

import json
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple


Poster = Callable[[str, bytes, Dict[str, str], float], Dict[str, Any]]


def _default_poster(url: str, body: bytes, headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read())


def _post_form(url: str, form: Dict[str, str], timeout: float,
                poster: Poster, basic_auth: Optional[Tuple[str, str]] = None) -> Dict[str, Any]:
    body = urllib.parse.urlencode(form).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if basic_auth is not None:
        import base64
        credentials = base64.b64encode(
            f"{basic_auth[0]}:{basic_auth[1]}".encode("utf-8")
        ).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"
    return poster(url, body, headers, timeout)


def fetch_client_credentials_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: Optional[str] = None,
    timeout: float = 5.0,
    poster: Poster = _default_poster,
) -> Dict[str, Any]:
    form: Dict[str, str] = {"grant_type": "client_credentials"}
    if scope:
        form["scope"] = scope
    return _post_form(token_url, form, timeout, poster,
                      basic_auth=(client_id, client_secret))


def fetch_password_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
    scope: Optional[str] = None,
    timeout: float = 5.0,
    poster: Poster = _default_poster,
) -> Dict[str, Any]:
    form: Dict[str, str] = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    if scope:
        form["scope"] = scope
    return _post_form(token_url, form, timeout, poster,
                      basic_auth=(client_id, client_secret))


def refresh_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    refresh: str,
    timeout: float = 5.0,
    poster: Poster = _default_poster,
) -> Dict[str, Any]:
    form: Dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }
    return _post_form(token_url, form, timeout, poster,
                      basic_auth=(client_id, client_secret))


@dataclass
class _CacheEntry:
    token: Dict[str, Any]
    expires_at: float


@dataclass
class OAuth2Client:
    token_url: str
    client_id: str
    client_secret: str
    scope: Optional[str] = None
    timeout: float = 5.0
    safety_window: float = 30.0
    poster: Poster = field(default=_default_poster)
    _cache: Dict[Tuple[str, str], _CacheEntry] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _cache_key(self, grant_type: str, subject: str = "") -> Tuple[str, str]:
        return (grant_type, f"{self.scope or ''}::{subject}")

    def _store(self, key: Tuple[str, str], token: Dict[str, Any]) -> Dict[str, Any]:
        expires_in = float(token.get("expires_in", 0))
        expires_at = time.time() + max(0.0, expires_in - self.safety_window)
        self._cache[key] = _CacheEntry(token=token, expires_at=expires_at)
        return token

    def _hit(self, key: Tuple[str, str]) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(key)
        if entry is None or entry.expires_at <= time.time():
            return None
        return entry.token

    def get_client_credentials(self) -> Dict[str, Any]:
        key = self._cache_key("client_credentials")
        with self._lock:
            cached = self._hit(key)
            if cached is not None:
                return cached
            token = fetch_client_credentials_token(
                self.token_url, self.client_id, self.client_secret,
                scope=self.scope, timeout=self.timeout, poster=self.poster,
            )
            return self._store(key, token)

    def get_password(self, username: str, password: str) -> Dict[str, Any]:
        key = self._cache_key("password", username)
        with self._lock:
            cached = self._hit(key)
            if cached is not None:
                return cached
            token = fetch_password_token(
                self.token_url, self.client_id, self.client_secret,
                username=username, password=password,
                scope=self.scope, timeout=self.timeout, poster=self.poster,
            )
            return self._store(key, token)

    def refresh(self, refresh: str) -> Dict[str, Any]:
        token = refresh_token(
            self.token_url, self.client_id, self.client_secret, refresh,
            timeout=self.timeout, poster=self.poster,
        )
        return self._store(self._cache_key("refresh", refresh), token)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

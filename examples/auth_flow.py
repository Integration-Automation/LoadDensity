"""
Auth flow recipe: extract a bearer token from a login response, then
reuse it on protected endpoints via ${var.auth}.
"""

from je_load_density import start_test


def main() -> None:
    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=20,
        spawn_rate=10,
        test_time=30,
        variables={"base": "https://httpbin.org"},
        tasks=[
            {"method": "post", "request_url": "${var.base}/post",
             "json": {"email": "u@example.com", "password": "secret"},  # NOSONAR example placeholder
             "extract": [
                 {"var": "auth", "from": "json_path",
                  "path": "json.password"},
             ]},
            {"method": "get", "request_url": "${var.base}/headers",
             "headers": {"Authorization": "Bearer ${var.auth}"},
             "assertions": [{"type": "status_code", "value": 200}]},
        ],
    )


if __name__ == "__main__":
    main()

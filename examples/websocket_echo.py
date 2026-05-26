"""
WebSocket echo recipe.

Requires the websocket extra: ``pip install "je_load_density[websocket]"``.
"""

from je_load_density import start_test


def main() -> None:
    start_test(
        user_detail_dict={"user": "websocket_user"},
        user_count=5, spawn_rate=2, test_time=20,
        tasks=[
            {"method": "connect",
             "request_url": "wss://echo.websocket.events"},
            {"method": "sendrecv", "payload": "ping",
             "expect": "echo", "timeout": 5},
            {"method": "close"},
        ],
    )


if __name__ == "__main__":
    main()

"""
HAR replay recipe: convert a browser-captured HAR file into a
runnable action JSON, then execute it.
"""

from je_load_density import execute_action, har_to_action_json, load_har


def main(har_path: str = "recording.har") -> None:
    har = load_har(har_path)
    action_json = har_to_action_json(
        har,
        user="fast_http_user",
        user_count=10,
        spawn_rate=5,
        test_time=60,
        include=[r"api\.example\.com"],
        exclude=[r"\.svg$", r"\.png$", r"analytics"],
    )
    execute_action(action_json)


if __name__ == "__main__":
    main()

"""
OpenAPI → action JSON recipe. Generates one task per (path, method)
and substitutes ``{param}`` path segments with ``${var.param}``.
"""

import json
import sys

from je_load_density import load_openapi, openapi_to_action_json


def main(spec_path: str = "openapi.json",
         out_path: str = "from_openapi.json") -> None:
    spec = load_openapi(spec_path)
    action_json = openapi_to_action_json(
        spec,
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=60,
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(action_json, fh, indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)

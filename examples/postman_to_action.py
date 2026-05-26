"""
Postman → action JSON recipe. Reads a v2.1 collection and emits an
LD_start_test action.
"""

import json
import sys

from je_load_density import load_postman_collection, postman_to_action_json


def main(collection_path: str = "collection.json",
         out_path: str = "from_postman.json") -> None:
    collection = load_postman_collection(collection_path)
    action_json = postman_to_action_json(
        collection,
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=60,
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(action_json, fh, indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)

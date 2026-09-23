"""Shape of the payload generators behind the security probes (fuzz, GraphQL, JWT, smuggling).

These build the requests an operator sends to their own service during an authorised test; the
tests pin structure and invariants, not the exact random values.
"""
import base64
import hashlib
import hmac
import json
import time

import pytest

from je_load_density.utils.security import fuzz, graphql_checks, jwt_attacks, smuggling_checks


def _decode(part):
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


# --- fuzz -------------------------------------------------------------------------------------

def test_mutate_string_variants_are_distinct_and_capped():
    variants = fuzz.mutate_string("abc", count=100)
    assert variants[0] == "abc"
    assert len(variants) == len(set(variants))
    assert len(fuzz.mutate_string("abc", count=3)) == 3


@pytest.mark.parametrize("seed", [{"a": 1, "b": "x"}, {}], ids=["fields", "empty"])
def test_mutate_json_returns_count_variants_and_keeps_the_seed(seed):
    original = dict(seed)
    variants = fuzz.mutate_json(seed, count=6)
    assert len(variants) == 6
    assert seed == original
    assert all(set(variant) <= set(seed) | set() for variant in variants)


@pytest.mark.parametrize("task", [
    {"method": "post", "request_url": "https://a.test/x", "json": {"a": 1}, "params": {"q": "1"}},
    {"method": "post", "request_url": "https://a.test/x", "json": {}},
    {"method": "get", "request_url": "https://a.test/x"},
], ids=["body-and-query", "empty-body", "nothing-to-fuzz"])
def test_expand_task_fuzz_keeps_the_url_and_returns_count_variants(task):
    variants = fuzz.expand_task_fuzz(task, count=4)
    assert len(variants) == 4
    assert all(variant["request_url"] == task["request_url"] for variant in variants)


def test_fuzz_query_string_adds_a_parameter_and_mutates_one():
    for variant in fuzz.fuzz_query_string({"q": "1"}, count=5):
        assert len(variant) == 2
        assert variant["q"] in fuzz.BAD_BYTES


def test_render_fuzz_payload_is_json_text():
    payload = json.loads(fuzz.render_fuzz_payload("seed"))
    assert list(fuzz.BAD_BYTES) == payload[:len(fuzz.BAD_BYTES)]


# --- GraphQL ----------------------------------------------------------------------------------

def test_depth_attack_nests_the_requested_depth():
    assert graphql_checks.build_depth_attack(depth=3)["query"] == "query Depth { node { node { node { id } } } }"
    assert graphql_checks.build_depth_attack(depth=0, leaf_field="x")["query"] == "{ x }"


def test_alias_batching_repeats_the_field_under_distinct_aliases():
    query = graphql_checks.build_alias_batching_attack(field="me", aliases=3)["query"]
    assert query == "query Batched { a0: me { id } a1: me { id } a2: me { id } }"
    assert graphql_checks.build_alias_batching_attack(aliases=0)["query"].count(": viewer") == 1


def test_attack_pack_has_the_three_probes():
    pack = graphql_checks.graphql_attack_pack(depth=2, aliases=2)
    assert set(pack) == {"introspection", "depth", "alias_batching"}
    assert "__schema" in pack["introspection"]["query"]


# --- JWT --------------------------------------------------------------------------------------

def test_alg_none_token_has_no_signature():
    header, body, signature = jwt_attacks.craft_alg_none_token({"sub": "1"}).split(".")
    assert _decode(header) == {"alg": "none", "typ": "JWT"}
    assert _decode(body) == {"sub": "1"}
    assert signature == ""


def test_expired_token_is_signed_and_in_the_past():
    token = jwt_attacks.craft_expired_token({"sub": "1"}, "k", seconds_ago=60)
    header, body, signature = token.split(".")
    assert _decode(body)["exp"] <= int(time.time()) - 60
    expected = hmac.new(b"k", f"{header}.{body}".encode("ascii"), hashlib.sha256).digest()
    assert base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)) == expected


def test_attack_pack_adds_confusion_only_with_a_public_key():
    assert set(jwt_attacks.craft_attack_pack({"sub": "1"})) == {"alg_none", "expired", "kid_traversal"}
    pack = jwt_attacks.craft_attack_pack({"sub": "1"}, public_key_pem="PEM")
    assert _decode(pack["rs_to_hs_confusion"].split(".")[0])["alg"] == "HS256"
    assert _decode(pack["kid_traversal"].split(".")[0])["kid"] == "../../dev/null"


# --- request smuggling ------------------------------------------------------------------------

def test_smuggling_pack_targets_the_host_with_both_length_headers():
    pack = smuggling_checks.smuggling_attack_pack("app.test", "/api")
    assert set(pack) == {"cl_te", "te_cl", "te_te"}
    for raw in pack.values():
        assert raw.startswith("POST /api HTTP/1.1\r\nHost: app.test\r\n")
        assert "transfer-encoding" in raw.lower()

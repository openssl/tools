# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The api.openssl.org client, against a stubbed transport."""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from openssl_tools.reviewtools.errors import QueryError
from openssl_tools.reviewtools.query import Query, ReviewMalformedID, encode_id, extract_email


class StubOpener:
    """Answers requests from a table of url -> (status, body)."""

    def __init__(self, routes):
        self.routes = routes
        self.requested: list[str] = []

    def open(self, request, timeout=None):
        url = request.full_url
        self.requested.append(url)
        status, body = self.routes.get(url, (404, ""))
        if status >= 400:
            raise urllib.error.HTTPError(
                url, status, f"status {status}", {}, io.BytesIO(body.encode())
            )
        return _Response(status, body)


class _Response:
    def __init__(self, status, body):
        self.status = status
        self._body = body.encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


BASE = "https://api.openssl.org"
STEVE = "Steve Henson <steve@openssl.org>"


def make_query(routes):
    return Query(BASE, opener=StubOpener(routes))


# -- identifier handling ----------------------------------------------------


def test_encode_id_passes_a_plain_string_through():
    assert encode_id("steve@openssl.org") == "steve@openssl.org"


def test_encode_id_renders_a_tagged_identity():
    assert encode_id({"github": "levitte"}) == "github:levitte"


def test_encode_id_rejects_an_ambiguous_mapping():
    with pytest.raises(ReviewMalformedID):
        encode_id({"github": "a", "ghe": "b"})


@pytest.mark.parametrize(
    "given,expected",
    [
        ("steve@openssl.org", "steve@openssl.org"),
        ("Steve Henson <steve@openssl.org>", "steve@openssl.org"),
        ("steve henson <steve@openssl.org>", "steve@openssl.org"),
    ],
)
def test_extract_email(given, expected):
    assert extract_email(given) == expected


@pytest.mark.parametrize("given", ["Steve Henson", "", "no at sign", "@handle"])
def test_extract_email_rejects_a_non_address(given):
    with pytest.raises(ReviewMalformedID):
        extract_email(given)


# -- endpoints --------------------------------------------------------------


def test_find_person_tag_returns_the_first_value():
    query = make_query(
        {
            f"{BASE}/0/Person/steve/ValueOfTag/rev": (200, json.dumps([STEVE])),
        }
    )

    assert query.find_person_tag("steve", "rev") == STEVE


def test_find_person_tag_is_none_for_an_unknown_person():
    assert make_query({}).find_person_tag("nobody", "rev") is None


def test_find_person_tag_percent_encodes_the_identity():
    opener = StubOpener({})
    Query(BASE, opener=opener).find_person_tag("a b/c", "rev")

    assert opener.requested == [f"{BASE}/0/Person/a%20b%2Fc/ValueOfTag/rev"]


def test_has_cla_percent_encodes_the_address():
    opener = StubOpener({})
    Query(BASE, opener=opener).has_cla("steve@openssl.org")

    assert opener.requested == [f"{BASE}/0/HasCLA/steve%40openssl.org"]


def test_has_cla_is_true_on_200():
    query = make_query({f"{BASE}/0/HasCLA/steve%40openssl.org": (200, "")})

    assert query.has_cla("steve@openssl.org")


def test_has_cla_accepts_a_full_reviewer_tag():
    query = make_query({f"{BASE}/0/HasCLA/steve%40openssl.org": (200, "")})

    assert query.has_cla(STEVE)


def test_has_cla_is_false_on_404():
    assert not make_query({}).has_cla("nobody@example.invalid")


def test_is_member_of():
    query = make_query(
        {f"{BASE}/0/Person/steve/IsMemberOf/commit": (200, json.dumps([1]))}
    )

    assert query.is_member_of("steve", "commit") is True
    assert query.is_member_of("steve", "otc") is False


def test_list_people_returns_the_decoded_array():
    records = [["steve", "steve@openssl.org"]]
    query = make_query({f"{BASE}/0/People": (200, json.dumps(records))})

    assert query.list_people() == records


def test_list_people_is_empty_when_absent():
    assert make_query({}).list_people() == []


def test_find_person_returns_a_dict():
    query = make_query({f"{BASE}/0/Person/steve": (200, json.dumps({"name": "s"}))})

    assert query.find_person("steve") == {"name": "s"}


def test_members_of():
    query = make_query({f"{BASE}/0/Group/commit/Members": (200, json.dumps(["a"]))})

    assert query.members_of("commit") == ["a"]


# -- failure handling -------------------------------------------------------


def test_a_server_error_is_raised_not_swallowed():
    # A 5xx means the database is broken; a 404 means "no such person".
    # Confusing the two would silently drop reviewers.
    query = make_query({f"{BASE}/0/People": (503, "unavailable")})

    with pytest.raises(QueryError, match="Server error"):
        query.list_people()


def test_an_unreachable_host_is_reported():
    class Broken:
        def open(self, request, timeout=None):
            raise urllib.error.URLError("no route to host")

    with pytest.raises(QueryError, match="Could not reach"):
        Query(BASE, opener=Broken()).list_people()


def test_malformed_json_is_reported():
    query = make_query({f"{BASE}/0/People": (200, "{not json")})

    with pytest.raises(QueryError, match="Malformed JSON"):
        query.list_people()


# -- caching ----------------------------------------------------------------


def test_repeated_lookups_hit_the_network_once():
    # --list asks three questions per person; without this it would be
    # unusably chatty.
    opener = StubOpener({f"{BASE}/0/HasCLA/steve%40openssl.org": (200, "")})
    query = Query(BASE, opener=opener)

    assert query.has_cla("steve@openssl.org")
    assert query.has_cla("steve@openssl.org")

    assert len(opener.requested) == 1


def test_negative_results_are_cached_too():
    opener = StubOpener({})
    query = Query(BASE, opener=opener)

    query.find_person_tag("nobody", "rev")
    query.find_person_tag("nobody", "rev")

    assert len(opener.requested) == 1

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Reviewer resolution and the policy checks.

These rules decide whether a change is allowed to be merged, so they are
covered case by case rather than in aggregate.
"""
from __future__ import annotations

import pytest

from reviewtools.errors import ReviewError
from reviewtools.policy import POLICIES, get_policy
from reviewtools.reviewers import require_any, resolve, validate

from conftest import LEVITTE, RICH, STEVE, FakePeople

OPENSSL = POLICIES["openssl"]
TOOLS = POLICIES["tools"]
FUZZ = POLICIES["fuzz-corpora"]


# -- resolution -------------------------------------------------------------


def test_a_short_name_resolves_to_a_reviewer_tag(people):
    result = resolve(people, ["steve"], author_email=None, policy=OPENSSL)

    assert result.reviewers == [STEVE]
    assert result.unknown == [] and result.nocla == []


def test_an_email_resolves(people):
    result = resolve(people, ["levitte@openssl.org"], author_email=None, policy=OPENSSL)

    assert result.reviewers == [LEVITTE]


def test_a_github_handle_has_its_at_sign_stripped(people):
    result = resolve(people, ["@snhenson"], author_email=None, policy=OPENSSL)

    assert result.reviewers == [STEVE]


def test_the_same_person_named_twice_is_credited_once(people):
    result = resolve(
        people, ["steve", "@snhenson"], author_email=None, policy=OPENSSL
    )

    assert result.reviewers == [STEVE]


def test_an_unknown_name_is_collected(people):
    result = resolve(people, ["whoisthis"], author_email=None, policy=OPENSSL)

    assert result.unknown == ["whoisthis"]
    assert result.nocla == ["whoisthis"]
    assert result.reviewers == []


def test_an_unknown_address_with_a_cla_is_unknown_but_not_claless(people):
    result = resolve(
        people, ["contributor@example.invalid"], author_email=None, policy=OPENSSL
    )

    assert result.unknown == ["contributor@example.invalid"]
    assert result.nocla == []


def test_a_known_person_without_a_cla_is_collected(people):
    result = resolve(people, ["nocla"], author_email=None, policy=OPENSSL)

    assert result.nocla == ["nocla"]
    assert result.unknown == []
    assert result.reviewers == []


# -- authors ----------------------------------------------------------------


def test_the_author_is_never_a_reviewer_in_the_main_repository(people):
    # min_authors == 0 means authors must not count at all.
    result = resolve(
        people,
        ["steve@openssl.org", "levitte"],
        author_email="steve@openssl.org",
        policy=OPENSSL,
    )

    assert result.reviewers == [LEVITTE]
    assert result.author_count == 0


def test_the_author_counts_where_the_policy_allows_it(people):
    result = resolve(
        people,
        ["steve@openssl.org", "levitte"],
        author_email="steve@openssl.org",
        policy=TOOLS,
    )

    assert result.author_count == 1
    # Counted, but still not given a Reviewed-by: trailer.
    assert result.reviewers == [LEVITTE]


def test_the_author_counts_on_a_release_run(people):
    result = resolve(
        people,
        ["steve@openssl.org", "levitte"],
        author_email="steve@openssl.org",
        policy=OPENSSL,
        release=True,
    )

    assert result.author_count == 1
    assert result.reviewers == [LEVITTE]


def test_the_author_named_twice_is_counted_once(people):
    # gitaddrev incremented authorcount per mention, because it deduplicated
    # against the reviewer list, which never contained authors.  The "No
    # reviewer set!" backstop hid the effect, but the count was wrong.
    result = resolve(
        people,
        ["steve@openssl.org", "steve", "@snhenson"],
        author_email="steve@openssl.org",
        policy=TOOLS,
    )

    assert result.author_count == 1
    assert result.reviewers == []


# -- validation -------------------------------------------------------------


def test_two_reviewers_satisfy_the_main_repository(people):
    result = resolve(people, ["steve", "levitte"], author_email=None, policy=OPENSSL)

    validate(result, author_email=None, policy=OPENSSL)


def test_one_reviewer_does_not(people):
    result = resolve(people, ["steve"], author_email=None, policy=OPENSSL)

    with pytest.raises(ReviewError, match="Too few reviewers .* at least 2"):
        validate(result, author_email=None, policy=OPENSSL)


def test_an_author_reduces_the_requirement_where_they_count(people):
    result = resolve(
        people,
        ["steve@openssl.org", "levitte"],
        author_email="steve@openssl.org",
        policy=TOOLS,
    )

    validate(result, author_email="steve@openssl.org", policy=TOOLS)


def test_fuzz_corpora_needs_only_one(people):
    result = resolve(people, ["steve"], author_email=None, policy=FUZZ)

    validate(result, author_email=None, policy=FUZZ)


def test_an_unknown_reviewer_aborts(people):
    result = resolve(
        people, ["steve", "levitte", "ghost"], author_email=None, policy=OPENSSL
    )

    with pytest.raises(ReviewError, match="Unknown reviewers: ghost"):
        validate(result, author_email=None, policy=OPENSSL)


def test_a_reviewer_without_a_cla_aborts(people):
    result = resolve(
        people, ["steve", "levitte", "nocla"], author_email=None, policy=OPENSSL
    )

    with pytest.raises(ReviewError, match="Reviewers without CLA: nocla"):
        validate(result, author_email=None, policy=OPENSSL)


def test_an_author_without_a_cla_aborts_on_a_non_trivial_commit(people):
    result = resolve(
        people,
        ["nocla@example.invalid", "steve", "levitte"],
        author_email="nocla@example.invalid",
        policy=OPENSSL,
    )

    with pytest.raises(ReviewError, match="has no CLA, and this is a non-trivial"):
        validate(result, author_email="nocla@example.invalid", policy=OPENSSL)


def test_an_author_without_a_cla_is_allowed_on_a_trivial_commit(people):
    result = resolve(
        people,
        ["nocla@example.invalid", "steve", "levitte"],
        author_email="nocla@example.invalid",
        policy=OPENSSL,
    )

    validate(
        result, author_email="nocla@example.invalid", policy=OPENSSL, trivial=True
    )


def test_the_author_is_not_reported_as_an_unknown_reviewer(people):
    # An author who is not in the database should produce the CLA error
    # above, not a confusing second complaint about unknown reviewers.
    result = resolve(
        people,
        ["someone@example.invalid", "steve", "levitte"],
        author_email="someone@example.invalid",
        policy=OPENSSL,
    )

    with pytest.raises(ReviewError, match="has no CLA"):
        validate(result, author_email="someone@example.invalid", policy=OPENSSL)

    # ...and with the CLA question settled, no further error.
    validate(
        result, author_email="someone@example.invalid", policy=OPENSSL, trivial=True
    )


def test_require_any_is_the_final_backstop():
    require_any([STEVE])
    with pytest.raises(ReviewError, match="No reviewer set!"):
        require_any([])


# -- transport failures -----------------------------------------------------


def test_a_database_outage_is_not_mistaken_for_a_missing_reviewer():
    class Broken(FakePeople):
        def has_cla(self, identity):
            from reviewtools.errors import QueryError

            raise QueryError("Server error: Service Unavailable")

    with pytest.raises(Exception, match="Server error"):
        resolve(Broken(), ["steve"], author_email=None, policy=OPENSSL)


# -- policies ---------------------------------------------------------------


def test_every_policy_names_a_repository():
    for name, policy in POLICIES.items():
        assert policy.name
        assert policy.min_reviewers >= 1


def test_web_points_at_the_web_repository():
    # gitaddrev had no --web branch, so web commits were labelled as openssl.
    assert get_policy("web").name == "web"


def test_an_unknown_repository_is_rejected():
    with pytest.raises(ReviewError, match="Unknown repository"):
        get_policy("nosuchrepo")


def test_no_policy_defaults_to_openssl():
    assert get_policy(None) is POLICIES["openssl"]

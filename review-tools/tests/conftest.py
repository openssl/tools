# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Shared fixtures.

Nothing here reaches api.openssl.org.  `FakePeople` stands in for the client
at the same interface, so the reviewer rules are tested against a known
database rather than whatever production happens to hold.

Note the shape of a 'rev' tag: it is the full `Name <email>` string that
ends up on a Reviewed-by: line, not a short handle.  That is why CLA lookups
have to pull the address back out of it.
"""
from __future__ import annotations

import time

import pytest

from reviewtools.query import extract_email

STEVE = "Steve Henson <steve@openssl.org>"
LEVITTE = "Richard Levitte <levitte@openssl.org>"
RICH = "Rich Salz <rich@openssl.org>"
NOCLA = "No Cla <nocla@example.invalid>"

#: Every identity the database resolves, mapped to its 'rev' tag.
PEOPLE = {
    "steve": STEVE,
    "steve@openssl.org": STEVE,
    "snhenson": STEVE,
    "levitte": LEVITTE,
    "levitte@openssl.org": LEVITTE,
    "richsalz": RICH,
    "rich@openssl.org": RICH,
    "nocla": NOCLA,
    "nocla@example.invalid": NOCLA,
}

#: Addresses with a CLA on file.
CLA_EMAILS = {
    "steve@openssl.org",
    "levitte@openssl.org",
    "rich@openssl.org",
    "contributor@example.invalid",
}

GROUPS = {"commit": {"steve@openssl.org", "levitte@openssl.org", "rich@openssl.org"}}


class FakePeople:
    """A stand-in for reviewtools.query.Query."""

    def __init__(self, people=None, cla_emails=None, groups=None):
        self.people = dict(PEOPLE if people is None else people)
        self.cla_emails = set(CLA_EMAILS if cla_emails is None else cla_emails)
        self.groups = dict(GROUPS if groups is None else groups)
        self.calls: list[tuple] = []

    def find_person_tag(self, identity, tag):
        self.calls.append(("find_person_tag", identity, tag))
        if tag != "rev":
            return None
        return self.people.get(identity)

    def has_cla(self, identity):
        self.calls.append(("has_cla", identity))
        # Uses the real extractor so the fake rejects the same inputs the
        # server-backed client would.
        return extract_email(identity).lower() in self.cla_emails

    def is_member_of(self, identity, group):
        self.calls.append(("is_member_of", identity, group))
        return identity in self.groups.get(group, set())

    def list_people(self):
        self.calls.append(("list_people",))
        return [
            ["steve", "steve@openssl.org", {"github": "snhenson"}],
            ["levitte", "levitte@openssl.org", {"github": "levitte"}],
            ["nocla", "nocla@example.invalid"],
        ]


@pytest.fixture
def people():
    return FakePeople()


#: A fixed gmtime, so MergeDate values are predictable.
FROZEN_TIME = time.struct_time((2026, 8, 25, 12, 34, 56, 1, 237, 0))
FROZEN_MERGE_DATE = "Tue Aug 25 12:34:56 2026"


@pytest.fixture
def frozen_time():
    return FROZEN_TIME

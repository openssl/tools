# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Listing the reviewers a commit may be attributed to.

Backs `addrev --list`.  A person is listed when they have a 'rev' tag, a CLA
on file, and membership of the 'commit' group -- and each of their usable
identities is shown against that tag, so any of them can be typed as a
reviewer name.

This asks the API three questions per person, so it is inherently slow; the
client caches within a run, but there is no bulk endpoint.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .reviewers import COMMIT_GROUP

#: Identities worth showing: a bare alphabetic name, or an '@handle'.  The
#: handle pattern is odd -- it accepts '@ab' and '@a-b' but not '@a-b-c' --
#: and is kept as it was so the listing does not change.
_PLAIN_NAME_RE = re.compile(r"^[A-Za-z]+$")
_HANDLE_RE = re.compile(r"^@(?:\w|\w-\w)+$")

#: Identity keys that name a GitHub or GitHub Enterprise account, whose
#: values are shown with a leading '@'.
_HANDLE_KEYS = ("github", "ghe")


def usable_identities(record: Iterable) -> list[str]:
    """The identities from one person record that can be typed as a reviewer."""
    flattened: list[str] = []
    for identity in record:
        if isinstance(identity, dict):
            for key, value in identity.items():
                flattened.append(f"@{value}" if key in _HANDLE_KEYS else str(value))
        else:
            flattened.append(str(identity))

    return sorted(
        name for name in flattened if _PLAIN_NAME_RE.match(name) or _HANDLE_RE.match(name)
    )


def primary_email(record: Iterable) -> str | None:
    """The first plain-string identity containing an '@', used for lookups."""
    for identity in record:
        if isinstance(identity, str) and "@" in identity:
            return identity
    return None


def list_reviewers(query) -> list[tuple[str, str]]:
    """(identity, reviewer tag) pairs, sorted by tag then identity."""
    found: dict[str, str] = {}

    for record in query.list_people():
        email = primary_email(record)
        if email is None:
            continue
        tag = query.find_person_tag(email, "rev")
        if tag is None:
            continue
        if not query.has_cla(tag.lower()):
            continue
        if not query.is_member_of(email, COMMIT_GROUP):
            continue
        for name in usable_identities(record):
            found[name] = tag

    return sorted(found.items(), key=lambda pair: (pair[1], pair[0]))


def format_listing(pairs: Iterable[tuple[str, str]]) -> str:
    return "".join(f"{name:<15}  ({tag})\n" for name, tag in pairs)

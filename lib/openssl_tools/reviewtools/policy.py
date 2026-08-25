# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""How many reviewers each repository requires."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ReviewError


@dataclass(frozen=True)
class RepoPolicy:
    """The review rules for one repository.

    `name` is the repository under github.com/openssl/ that a
    "(Merged from ...)" line should point at.

    `min_authors` is special: 0 means an author must **not** be counted as a
    reviewer at all.  Any other value is a minimum.  Do not collapse these
    two meanings -- the difference is what stops someone approving their own
    change in the main repository.
    """

    name: str
    min_reviewers: int
    min_authors: int


#: Keyed by the command line flag, without its leading dashes.
POLICIES: dict[str, RepoPolicy] = {
    # The main repository: two reviewers, and the author is never one of them.
    "openssl": RepoPolicy("openssl", min_reviewers=2, min_authors=0),
    "tools": RepoPolicy("tools", min_reviewers=2, min_authors=1),
    "perftools": RepoPolicy("perftools", min_reviewers=2, min_authors=1),
    "installer": RepoPolicy("installer", min_reviewers=2, min_authors=1),
    "fuzz-corpora": RepoPolicy("fuzz-corpora", min_reviewers=1, min_authors=1),
    # `--web` was accepted by addrev and forwarded, but gitaddrev had no
    # branch for it, so it silently fell through to the openssl policy and
    # wrote "(Merged from .../openssl/pull/N)" into web commits.  The name is
    # corrected here; the review counts are left at what they effectively
    # were, since no stricter policy was ever actually applied.
    "web": RepoPolicy("web", min_reviewers=2, min_authors=0),
    # `--technical-policies` reached addrev from ghmerge, matched none of its
    # patterns, and was silently used as a commit range -- which made
    # `ghmerge --technical-policies` fail on a bogus revision.
    "technical-policies": RepoPolicy("technical-policies", min_reviewers=2, min_authors=0),
}

DEFAULT_POLICY = POLICIES["openssl"]


def get_policy(name: str | None) -> RepoPolicy:
    if not name:
        return DEFAULT_POLICY
    try:
        return POLICIES[name]
    except KeyError as error:
        raise ReviewError(
            f"Unknown repository {name!r}; expected one of: " + ", ".join(sorted(POLICIES))
        ) from error

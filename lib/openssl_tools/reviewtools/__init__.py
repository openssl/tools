# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""OpenSSL PR review helpers.

Standard library only, so these can be symlinked into /usr/local/bin on a
provisioned host without pulling in a package manager.

The public entry point for other tools is `add_reviewers`, which resolves
reviewer names against the committer database and returns a rewritten commit
message.  release-tools uses it directly, rather than shelling out to the
`addrev` script and needing it on PATH.
"""
from __future__ import annotations

from typing import Sequence

from . import message as _message
from . import reviewers as _reviewers
from .errors import QueryError, ReviewError
from .policy import POLICIES, RepoPolicy, get_policy
from .query import Query

__version__ = "1.0.0"

__all__ = [
    "POLICIES",
    "Query",
    "QueryError",
    "RepoPolicy",
    "ReviewError",
    "add_reviewers",
    "get_policy",
    "resolve_reviewers",
]


def resolve_reviewers(
    candidates: Sequence[str],
    *,
    author_email: str | None,
    repo: str = "openssl",
    release: bool = False,
    query=None,
) -> list[str]:
    """Validate explicitly named reviewers and return their tags.

    `candidates` are names the caller asked for, so each must belong to a
    committer.  `author_email` is collected automatically and is held to the
    laxer standard described in reviewers.py.

    Raises ReviewError if a name is unknown, has no CLA, is not a committer,
    or the repository's minimum is not met; QueryError if the database cannot
    be reached.
    """
    query = query or Query()
    policy = get_policy(repo)
    resolution = _reviewers.resolve(
        query,
        candidates,
        author_email=author_email,
        policy=policy,
        release=release,
    )
    _reviewers.validate(
        resolution, author_email=author_email, policy=policy, trivial=False
    )
    _reviewers.require_any(resolution.reviewers)
    return resolution.reviewers


def add_reviewers(
    commit_message: str,
    candidates: Sequence[str],
    *,
    author_email: str | None,
    repo: str = "openssl",
    release: bool = False,
    prnum: str | None = None,
    query=None,
) -> str:
    """Return `commit_message` with validated Reviewed-by: trailers added."""
    tags = resolve_reviewers(
        candidates,
        author_email=author_email,
        repo=repo,
        release=release,
        query=query,
    )
    return _message.rewrite(
        commit_message,
        reviewers=tags,
        repo=get_policy(repo).name,
        prnum=prnum,
        release=release,
    )

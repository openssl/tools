# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Adding Reviewed-by: trailers to the commits this tool makes.

Two steps, deliberately separated:

`resolve` validates the reviewer names against the committer and CLA
databases.  It runs once, as a preflight check, before anything is written
or built -- a name that turns out not to belong to a committer should not
cost the caller a `make update` first.

`credit` then amends a commit's message with the tags `resolve` returned.
It does no lookups, so the five commits a staging run makes cost one round
trip between them rather than five.

The shell ran `addrev --release --nopr --reviewer=...` after each commit,
which needed addrev on PATH, re-queried the database every time, and drove
`git filter-branch` over a commit created seconds earlier.
"""
from __future__ import annotations

from typing import Sequence

from ..reviewtools import ReviewError, resolve_reviewers
from ..reviewtools import message as review_message
from .errors import ReleaseError
from .git import Git

#: The commits this tool makes are release commits in the openssl repository,
#: and carry a `Release: yes` line but no "(Merged from ...)" reference --
#: what `addrev --release --nopr` produced.
REPO = "openssl"


def resolve(
    git: Git,
    candidates: Sequence[str],
    *,
    author_email: str | None = None,
    query=None,
) -> list[str]:
    """Validate reviewer names and return their Reviewed-by: tags.

    Raises ReleaseError if any name is unknown, has no CLA, is not a
    committer, or if too few reviewers were named for the repository.
    """
    if not candidates:
        return []

    if author_email is None:
        author_email = git.user_email()

    try:
        return resolve_reviewers(
            candidates,
            author_email=author_email,
            repo=REPO,
            release=True,
            query=query,
        )
    except ReviewError as error:
        raise ReleaseError(f"Reviewer check failed: {error}") from error


def credit(git: Git, tags: Sequence[str]) -> None:
    """Amend HEAD's message with already-validated Reviewed-by: tags."""
    if not tags:
        return
    git.amend_message(
        review_message.rewrite(
            git.head_message(),
            reviewers=tags,
            repo=REPO,
            release=True,
            prnum=None,
        )
    )

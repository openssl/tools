# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Adding Reviewed-by: trailers to the commits this tool makes.

The shell ran `addrev --release --nopr --reviewer=...`, which needed addrev
on PATH and drove `git filter-branch` over the commit just made.  Both are
avoidable: reviewtools is a sibling directory in this same repository, and
amending a commit we created seconds ago does not need filter-branch.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from .errors import ReleaseError
from .git import Git

#: review-tools sits beside release-tools in the tools repository.  There is
#: no install step for either, so the path is resolved relative to this file
#: rather than looked up on PATH or in site-packages.
REVIEW_TOOLS_DIR = Path(__file__).resolve().parents[2] / "review-tools"


def _load_reviewtools():
    if str(REVIEW_TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(REVIEW_TOOLS_DIR))
    try:
        import reviewtools
    except ImportError as error:
        raise ReleaseError(
            f"Could not import reviewtools from {REVIEW_TOOLS_DIR}",
            "release-tools and review-tools must both be present in the"
            " tools repository checkout.",
        ) from error
    return reviewtools


def add_reviewers(
    git: Git,
    candidates: Sequence[str],
    *,
    author_email: str | None = None,
    query=None,
) -> list[str]:
    """Amend HEAD's message with validated Reviewed-by: trailers.

    Returns the reviewer tags that were added.  Does nothing, and reaches no
    network, when no reviewers were asked for.
    """
    if not candidates:
        return []

    reviewtools = _load_reviewtools()

    if author_email is None:
        author_email = git.user_email()

    original = git.head_message()
    try:
        rewritten = reviewtools.add_reviewers(
            original,
            candidates,
            author_email=author_email,
            repo="openssl",
            # Matches the shell's `addrev --release --nopr`: a Release: yes
            # line, and no "(Merged from ...)" reference.
            release=True,
            prnum=None,
            query=query,
        )
    except reviewtools.ReviewError as error:
        raise ReleaseError(f"Could not add reviewers: {error}") from error

    git.amend_message(rewritten)
    return [
        line.split(":", 1)[1].strip()
        for line in rewritten.splitlines()
        if line.startswith("Reviewed-by:")
    ]

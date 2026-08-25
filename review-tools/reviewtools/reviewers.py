# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Turning reviewer names into validated Reviewed-by: tags.

The rules, carried over from gitaddrev:

- A reviewer may be named by anything the person database recognises: a
  short name, an email address, or a GitHub handle with a leading '@'.  The
  '@' is stripped before lookup.
- Every reviewer must resolve to a person with a 'rev' tag, and that person
  must have a CLA on file.
- Whether the commit's own author counts towards the reviewer total depends
  on the repository policy: `min_authors == 0` means they do not.  A release
  run counts them regardless.
- Authors never get a Reviewed-by: trailer, even when they count.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol, Sequence

from .errors import QueryError, ReviewError
from .policy import RepoPolicy


class PersonSource(Protocol):
    """The slice of the API client this module needs."""

    def find_person_tag(self, identity: str, tag: str) -> str | None: ...
    def has_cla(self, identity: str) -> bool: ...


@dataclass
class Resolution:
    """The outcome of looking every candidate up."""

    #: Reviewer tags to write as Reviewed-by: trailers, in the order given.
    reviewers: list[str] = field(default_factory=list)
    #: How many distinct authors were counted towards the reviewer total.
    author_count: int = 0
    #: Candidates the person database does not know.
    unknown: list[str] = field(default_factory=list)
    #: Candidates with no CLA on file.
    nocla: list[str] = field(default_factory=list)


def _strip_handle(identity: str) -> str:
    """'@someone' -> 'someone'; anything else unchanged."""
    return identity[1:] if identity.startswith("@") else identity


def _has_cla_quietly(source: PersonSource, identity: str) -> bool:
    """has_cla, treating a malformed identifier as 'no CLA' rather than error.

    An arbitrary reviewer name is not necessarily an email address, and the
    Perl relied on a regex guard before asking.  Swallowing the error here
    keeps that behaviour while letting genuine transport failures through.
    """
    try:
        return source.has_cla(identity)
    except QueryError as error:
        if "Malformed" in str(error):
            return False
        raise


def resolve(
    source: PersonSource,
    candidates: Iterable[str],
    *,
    author_email: str | None,
    policy: RepoPolicy,
    release: bool = False,
) -> Resolution:
    """Look up every candidate and sort them into reviewers, unknown, no-CLA."""
    result = Resolution()

    author_tag = None
    if author_email:
        author_tag = source.find_person_tag(author_email, "rev")

    def is_author(tag: str) -> bool:
        return author_tag is not None and tag == author_tag

    # Distinct resolved tags seen so far, authors included.  The Perl tracked
    # this by scanning the reviewer list, which never contained authors, so an
    # author named twice -- as the commit author and again via --reviewer --
    # was counted twice and lowered the effective reviewer requirement.  The
    # "No reviewer set!" backstop masked it in every configuration, but the
    # count was still wrong.
    seen: set[str] = set()

    for candidate in candidates:
        if not candidate:
            continue
        tag = source.find_person_tag(_strip_handle(candidate), "rev")

        if tag is None:
            if candidate not in result.unknown:
                result.unknown.append(candidate)
            # An unrecognised name might still be an email address with a CLA,
            # in which case it is "unknown" but not "no CLA".
            looks_like_email = "@" in candidate[1:] if candidate else False
            if not (looks_like_email and _has_cla_quietly(source, candidate.lower())):
                if candidate not in result.nocla:
                    result.nocla.append(candidate)
            continue

        if not source.has_cla(tag.lower()):
            if candidate not in result.nocla:
                result.nocla.append(candidate)
            continue

        if is_author(tag) and not (policy.min_authors > 0 or release):
            # This repository does not let authors count as reviewers.
            continue

        if tag in seen:
            continue
        seen.add(tag)

        if is_author(tag):
            result.author_count += 1
        else:
            result.reviewers.append(tag)

    return result


def validate(
    resolution: Resolution,
    *,
    author_email: str | None,
    policy: RepoPolicy,
    trivial: bool = False,
) -> None:
    """Raise ReviewError if the resolved set does not satisfy the policy."""
    # The author's own CLA is checked first, and separately: a trivial commit
    # is allowed from someone who has not signed one.
    if not trivial and author_email and author_email in resolution.nocla:
        raise ReviewError(
            f"Commit author {author_email} has no CLA,"
            " and this is a non-trivial commit"
        )

    # Now that that is settled, drop the author from both lists so they cannot
    # produce a second, confusing error.
    unknown = [name for name in resolution.unknown if name != author_email]
    nocla = [name for name in resolution.nocla if name != author_email]

    if unknown:
        raise ReviewError("Unknown reviewers: " + ", ".join(unknown))
    if nocla:
        raise ReviewError("Reviewers without CLA: " + ", ".join(nocla))

    required = policy.min_reviewers - resolution.author_count
    if len(resolution.reviewers) < required:
        raise ReviewError(f"Too few reviewers (total must be at least {required})")


def require_any(reviewers: Sequence[str]) -> None:
    """The final backstop: never rewrite a message with nobody credited."""
    if not reviewers:
        raise ReviewError("No reviewer set!")

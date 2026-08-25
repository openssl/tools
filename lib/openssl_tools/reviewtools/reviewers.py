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
- Every reviewer must resolve to a person with a 'rev' tag, that person must
  have a CLA on file, and they must be a committer.
- Whether the commit's own author counts towards the reviewer total depends
  on the repository policy: `min_authors == 0` means they do not.  A release
  run counts them regardless.
- Authors never get a Reviewed-by: trailer, even when they count.

Explicitly named reviewers and automatically collected identities are held
to different standards, and the difference matters.  Naming someone with
--reviewer asserts that they reviewed the change, so a non-committer there
is an error.  The author's address and git's user.email are picked up
without being asked for, so a non-committer there simply does not count --
erroring would make an outside contributor's patch unmergeable.

Note that one person can arrive by both routes: `--reviewer=<yourself>` on
a commit you authored is an explicit claim, and is checked as one.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from .errors import QueryError, ReviewError
from .policy import RepoPolicy

#: The group a person must belong to before their name can appear on a
#: Reviewed-by: line.  `addrev --list` has always filtered its output by this
#: same group; now the validation agrees with the listing.
COMMIT_GROUP = "commit"


class PersonSource(Protocol):
    """The slice of the API client this module needs.

    A Protocol rather than the concrete Query, so the tests can substitute a
    known database -- and so mypy checks that a substitute really does match
    the interface.
    """

    def find_person_tag(self, identity: str, tag: str) -> str | None: ...
    def has_cla(self, identity: str) -> bool: ...
    def is_member_of(self, identity: str, group: str) -> bool: ...


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
    #: Known, CLA-holding candidates who are not in the commit group.
    noncommitters: list[str] = field(default_factory=list)


def _strip_handle(identity: str) -> str:
    """'@someone' -> 'someone'; anything else unchanged."""
    return identity.removeprefix("@")


def _record(bucket: list[str], candidate: str) -> None:
    """Add `candidate` to `bucket` once, preserving the order given."""
    if candidate not in bucket:
        bucket.append(candidate)


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
    named: Iterable[str],
    *,
    author_email: str | None,
    policy: RepoPolicy,
    self_email: str | None = None,
    release: bool = False,
) -> Resolution:
    """Look up every candidate and sort them into reviewers, unknown, no-CLA.

    `named` are the reviewers the caller asked for explicitly.  They must be
    committers: naming someone is an assertion that they reviewed the change,
    and only a committer can make that assertion count.

    `author_email` and `self_email` are picked up automatically -- from the
    commit being rewritten and from git's user.email -- so they are treated
    differently.  If they are not committers they simply do not count towards
    the total; that is not an error, because an outside contributor's patch
    still has to be mergeable.
    """
    result = Resolution()

    # One person can appear twice -- as the author and again by name -- and
    # the lookup is a network round trip, so remember what we asked.
    tags: dict[str, str | None] = {}

    def lookup(identity: str) -> str | None:
        if identity not in tags:
            tags[identity] = source.find_person_tag(identity, "rev")
        return tags[identity]

    author_tag = lookup(author_email) if author_email else None

    def is_author(tag: str) -> bool:
        return author_tag is not None and tag == author_tag

    # (identity, was it named explicitly)
    queue: list[tuple[str, bool]] = [
        (identity, False) for identity in (author_email, self_email) if identity
    ]
    queue += [(identity, True) for identity in named if identity]

    # Distinct resolved tags seen so far, authors included.  The Perl tracked
    # this by scanning the reviewer list, which never contained authors, so an
    # author named twice -- as the commit author and again via --reviewer --
    # was counted twice and lowered the effective reviewer requirement.
    seen: set[str] = set()

    for candidate, explicit in queue:
        identity = _strip_handle(candidate)
        tag = lookup(identity)

        if tag is None:
            _record(result.unknown, candidate)
            # An unrecognised name might still be an email address with a CLA,
            # in which case it is "unknown" but not "no CLA".
            looks_like_email = "@" in candidate[1:] if candidate else False
            has_cla = looks_like_email and _has_cla_quietly(source, candidate.lower())
            if not has_cla:
                _record(result.nocla, candidate)
            continue

        if not source.has_cla(tag.lower()):
            _record(result.nocla, candidate)
            continue

        author = is_author(tag)
        if author and not (policy.min_authors > 0 or release):
            # This repository does not let authors count as reviewers at all,
            # so there is nothing further to check.
            continue

        if not source.is_member_of(identity, COMMIT_GROUP):
            if explicit:
                _record(result.noncommitters, candidate)
            # Otherwise: picked up automatically, so silently does not count.
            continue

        if tag in seen:
            continue
        seen.add(tag)

        if author:
            # Counted, but authors never get a Reviewed-by: trailer.
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
            f"Commit author {author_email} has no CLA, and this is a non-trivial commit"
        )

    # Now that that is settled, drop the author from both lists so they cannot
    # produce a second, confusing error.
    unknown = [name for name in resolution.unknown if name != author_email]
    nocla = [name for name in resolution.nocla if name != author_email]

    if unknown:
        raise ReviewError("Unknown reviewers: " + ", ".join(unknown))
    if nocla:
        raise ReviewError("Reviewers without CLA: " + ", ".join(nocla))
    if resolution.noncommitters:
        raise ReviewError(
            "Reviewers who are not committers: "
            + ", ".join(resolution.noncommitters)
            + "\nOnly committers may be credited on a Reviewed-by: line."
            " Run 'addrev --list' to see who those are."
        )

    required = policy.min_reviewers - resolution.author_count
    if len(resolution.reviewers) < required:
        raise ReviewError(f"Too few reviewers (total must be at least {required})")


def require_any(reviewers: Sequence[str]) -> None:
    """The final backstop: never rewrite a message with nobody credited."""
    if not reviewers:
        raise ReviewError("No reviewer set!")

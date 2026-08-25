# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Rewriting a commit message's trailers.

A pure function: message in, message out.  That is what lets stage-release
reuse this without spawning anything, and what makes the behaviour below
testable without a repository.

Trailer handling, carried over from gitaddrev:

- Existing `Reviewed-by:` lines are kept, and any reviewer already credited
  is not added a second time.
- A `(Merged from ...)` line is always dropped, and re-added only when a PR
  number was supplied.  So a run with `--nopr` removes it.
- `Release: yes` is dropped and re-appended on a release run, to keep it
  below the reviewer trailers.
- `MergeDate:` is added unless the message already has one.
"""
from __future__ import annotations

import re
import time
from typing import Sequence

TRIVIAL_RE = re.compile(r"^CLA:\s*Trivial\s*$", re.IGNORECASE)
REVIEWED_BY_RE = re.compile(r"^Reviewed-by:\s*(\S.*\S)\s*$")
RELEASE_RE = re.compile(r"^Release:\s*yes\s*$", re.IGNORECASE)
MERGE_DATE_RE = re.compile(r"^MergeDate: ")


def merged_from_prefix(repo: str) -> str:
    return f"(Merged from https://github.com/openssl/{repo}/pull/"


def split_lines(message: str) -> list[str]:
    """Split a commit message the way `while (<STDIN>)` did.

    On newlines only -- not on the form feeds and Unicode separators that
    str.splitlines() also breaks on -- with a trailing carriage return
    removed from each line.
    """
    lines = message.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def is_trivial(message: str) -> bool:
    """Whether the message carries a `CLA: Trivial` marker."""
    return any(TRIVIAL_RE.match(line) for line in split_lines(message))


def format_merge_date(when: time.struct_time | None = None) -> str:
    """The MergeDate value, in the format Perl's `scalar gmtime` produced."""
    return time.asctime(when or time.gmtime())


def rewrite(
    message: str,
    *,
    reviewers: Sequence[str],
    repo: str,
    prnum: str | None = None,
    release: bool = False,
    remove_reviewers: bool = False,
    now: time.struct_time | None = None,
) -> str:
    """Return `message` with its trailers brought up to date."""
    prefix = merged_from_prefix(repo)

    lines = split_lines(message)
    # Trailing blank lines would otherwise end up in the middle of the
    # message once trailers are appended.
    while lines and not lines[-1].strip():
        lines.pop()

    remaining = list(reviewers)
    out: list[str] = []
    last_is_trailer = False
    has_merge_date = False

    for line in lines:
        last_is_trailer = False

        if line.startswith(prefix):
            # Dropped either way; re-added below only if a PR number is known.
            if not remove_reviewers:
                last_is_trailer = True
            continue

        reviewed_by = REVIEWED_BY_RE.match(line)
        if reviewed_by:
            if remove_reviewers:
                continue
            last_is_trailer = True
            already_credited = reviewed_by.group(1)
            remaining = [r for r in remaining if r != already_credited]
            out.append(line)
            continue

        if RELEASE_RE.match(line):
            if release:
                continue
            out.append(line)
            continue

        if MERGE_DATE_RE.match(line):
            has_merge_date = True

        out.append(line)

    if not remove_reviewers:
        # Separate the trailers from the body, unless we are already in a
        # run of them.
        if not last_is_trailer:
            out.append("")
        out.extend(f"Reviewed-by: {reviewer}" for reviewer in remaining)

    if not has_merge_date:
        out.append(f"MergeDate: {format_merge_date(now)}")

    if release:
        out.append("Release: yes")

    if prnum:
        out.append(f"{prefix}{prnum})")

    return "".join(f"{line}\n" for line in out)

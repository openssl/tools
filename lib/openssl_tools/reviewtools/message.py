# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Rewriting a commit message's trailers.

The lines this tool manages are stripped from the body and re-added through
`git interpret-trailers --if-exists addIfDifferent`, which is what places
them in an existing trailer block, adds the separating blank line when the
message needs one, and drops a trailer that is already present verbatim.

Delegating that to git rather than reimplementing it is deliberate: this
replaces a script that does the same, and matching its output exactly
matters more than avoiding a subprocess.

Trailers produced:

- `Reviewed-by:` per reviewer, unless reviewers are being removed.
- `Merge-date:` unless the message already carries one.
- `Release: yes` on a release run.
- `Merged-from:` when a pull request number is known.
"""

from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable, Sequence

from .errors import ReviewError

TRIVIAL_RE = re.compile(r"^CLA:\s*Trivial\s*$", re.IGNORECASE)
REVIEWED_BY_RE = re.compile(r"^Reviewed-by:\s*\S", re.IGNORECASE)
RELEASE_RE = re.compile(r"^Release:\s*yes\s*$", re.IGNORECASE)
MERGE_DATE_RE = re.compile(r"^Merge-?date:\s*\S", re.IGNORECASE)
MERGED_FROM_RE = re.compile(r"^Merged-from:\s*\S", re.IGNORECASE)

#: The prose form of the merge reference, as commit messages carried it before
#: it became a trailer.  Still recognised so that re-running over an older
#: commit replaces it rather than leaving both.
LEGACY_MERGED_FROM = "(Merged from https://github.com/openssl/{repo}/pull/"

#: What a Merged-from: trailer points at.
MERGED_FROM_URL = "https://github.com/openssl/{repo}/pull/{prnum}"


def merged_from_url(repo: str, prnum: str) -> str:
    return MERGED_FROM_URL.format(repo=repo, prnum=prnum)


def split_lines(message: str) -> list[str]:
    """Split a commit message into lines, without their terminators.

    Splits on '\n' only, not str.splitlines(), which also breaks on form
    feeds and several Unicode separators; rejoining those would silently
    rewrite them.  A trailing carriage return is dropped, as Perl's `<STDIN>`
    plus `s|\\R$||` did.
    """
    lines = message.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.removesuffix("\r") for line in lines]


def is_trivial(message: str) -> bool:
    """Whether the message carries a `CLA: Trivial` marker."""
    return any(TRIVIAL_RE.match(line) for line in split_lines(message))


def format_merge_date(when: time.struct_time | None = None) -> str:
    """The Merge-date value, in the format Perl's `scalar gmtime` produced."""
    return time.asctime(when or time.gmtime())


def interpret_trailers(body: str, trailers: Sequence[str]) -> str:
    """Add `trailers` to `body` using git's own trailer handling."""
    argv = ["git", "interpret-trailers", "--if-exists", "addIfDifferent"]
    for trailer in trailers:
        argv += ["--trailer", trailer]

    completed = subprocess.run(  # noqa: S603
        argv, input=body, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ReviewError(
            "git interpret-trailers failed: "
            + ((completed.stderr or "").strip() or f"exit {completed.returncode}")
        )
    return completed.stdout


def rewrite(
    message: str,
    *,
    reviewers: Sequence[str],
    repo: str,
    prnum: str | None = None,
    release: bool = False,
    remove_reviewers: bool = False,
    now: time.struct_time | None = None,
    add_trailers: Callable[[str, Sequence[str]], str] = interpret_trailers,
) -> str:
    """Return `message` with its trailers brought up to date."""
    legacy_merged_from = LEGACY_MERGED_FROM.format(repo=repo)

    lines = split_lines(message)
    # Trailing blank lines would otherwise separate the body from the trailer
    # block twice over.
    while lines and not lines[-1].strip():
        lines.pop()

    body: list[str] = []
    has_merge_date = False

    for line in lines:
        if line.startswith(legacy_merged_from) or MERGED_FROM_RE.match(line):
            # Re-added below as a trailer, if a PR number is known.
            continue

        if REVIEWED_BY_RE.match(line):
            if remove_reviewers:
                continue
            # Otherwise kept: addIfDifferent deduplicates it against the
            # reviewers we are about to add.
        elif RELEASE_RE.match(line):
            if release:
                continue
        elif MERGE_DATE_RE.match(line):
            has_merge_date = True

        body.append(line)

    # Dropping a managed line can leave a blank at the end of the body, which
    # would separate it from the trailer block twice over.
    while body and not body[-1].strip():
        body.pop()

    trailers: list[str] = []
    if not remove_reviewers:
        trailers += [f"Reviewed-by: {reviewer}" for reviewer in reviewers]
    if not has_merge_date:
        trailers.append(f"Merge-date: {format_merge_date(now)}")
    if release:
        trailers.append("Release: yes")
    if prnum:
        trailers.append(f"Merged-from: {merged_from_url(repo, prnum)}")

    return add_trailers("\n".join(body) + "\n", trailers)

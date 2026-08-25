# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Finding commits eligible for cherry-picking between two branches.

Lists the symmetric difference of two branches, marking which commits have
an equivalent on the other side.  See `--cherry-mark` in git-log(1).

The subprocess calls are confined to `GitLog` so the parsing, sorting and
formatting below can be tested directly.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

from .errors import ReviewError

#: Where a commit lives: only on the left, only on the right, or both.
BRANCH_MARKERS = {"<": "<-", ">": "->", "=": "=="}

#: The standard merge annotation, plus an older variant still in the history.
_PRNUM_RE = re.compile(
    r"\(Merged from https://github\.com/openssl/openssl/pull/(\d+)\)"
    r"|GH: #(\d+)"
)

_FIXES_RE = re.compile(r"Fixes:?\s+(?:#|https://github\.com/openssl/openssl/pull/)(\d+)")

_RELEASE_BRANCH_RE = re.compile(r"^(?:.*/)?openssl-(\d+)\.(\d+)$")

#: A separator that cannot occur in a commit subject.
_FIELD_SEP = "\x1f"


@dataclass(frozen=True)
class Commit:
    prnum: str
    fixes: str
    timestamp: int
    branch: str
    commit: str
    subject: str

    @property
    def sort_key(self) -> tuple:
        """Order by PR number then author date, newest first.

        The PR number is compared numerically; comparing the strings put
        #9999 above #10000.  Commits with no discoverable PR sort last.
        """
        numeric = int(self.prnum) if self.prnum.isdigit() else -1
        return (numeric, self.timestamp)


def extract_prnum(message: str) -> str:
    match = _PRNUM_RE.search(message)
    if not match:
        return "????"
    return match.group(1) or match.group(2)


def extract_fixes(message: str) -> str:
    match = _FIXES_RE.search(message)
    return f"#{match.group(1)}" if match else ""


def shorten(subject: str, limit: int = 70) -> str:
    return subject if len(subject) <= limit else subject[:limit] + "..."


def pick_default_right(branches: Iterable[str]) -> str | None:
    """The highest openssl-N.M branch among `branches`.

    Chosen at run time rather than hardcoded, because the previous default
    was OpenSSL_1_1_1-stable and had been end-of-life for years.
    """
    best: tuple[tuple[int, int], str] | None = None
    for branch in branches:
        match = _RELEASE_BRANCH_RE.match(branch.strip())
        if not match:
            continue
        version = (int(match.group(1)), int(match.group(2)))
        if best is None or version > best[0]:
            best = (version, branch.strip())
    return best[1] if best else None


class GitLog:
    """The git commands this tool runs."""

    def __init__(self, runner=subprocess.run) -> None:
        self._runner = runner

    def _capture(self, argv: Sequence[str]) -> str:
        completed = self._runner(argv, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ReviewError(f"{' '.join(argv)} failed: {(completed.stderr or '').strip()}")
        return completed.stdout or ""

    def remotes(self) -> str:
        return self._capture(["git", "remote", "-v"])

    def branches(self) -> list[str]:
        output = self._capture(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"])
        return output.splitlines()

    def master_remote(self) -> str:
        """The remote master tracks, defaulting to origin.

        The Perl-era code called a non-existent `.trim()` here, so the
        AttributeError was swallowed by a bare `except` and this always
        returned "origin" -- making `--remote` ignore the configuration.
        """
        completed = self._runner(
            ["git", "config", "branch.master.remote"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return "origin"
        return (completed.stdout or "").strip() or "origin"

    def symmetric_difference(self, left: str, right: str) -> list[str]:
        return self._capture(
            [
                "git",
                "log",
                "--cherry-mark",
                "--left-right",
                f"{left}...{right}",
                f"--pretty=%at{_FIELD_SEP}%m{_FIELD_SEP}%h{_FIELD_SEP}%s",
            ]
        ).splitlines()

    def message(self, commit: str) -> str:
        return self._capture(["git", "show", "--no-patch", commit])


def is_openssl_repo(git: GitLog) -> bool:
    """Whether the current directory is a clone of openssl.git.

    A failing `git remote -v` -- typically because this is not a repository
    at all -- answers the question just as well as an empty remote list, so
    it is not worth surfacing as an error of its own.
    """
    try:
        return "/openssl.git" in git.remotes()
    except ReviewError:
        return False


def parse_log_line(line: str) -> tuple[int, str, str, str] | None:
    """(timestamp, branch marker, abbreviated id, subject) from one log line."""
    parts = line.split(_FIELD_SEP, 3)
    if len(parts) != 4:
        return None
    timestamp, branch, commit, subject = parts
    if not timestamp.isdigit() or branch not in BRANCH_MARKERS:
        return None
    return int(timestamp), branch, commit, subject


def pick_cherries(
    git: GitLog, left: str, right: str, *, include_picked: bool = False
) -> Iterator[Commit]:
    """Commits in `left...right`, skipping already-picked ones by default."""
    for line in git.symmetric_difference(left, right):
        parsed = parse_log_line(line)
        if parsed is None:
            continue
        timestamp, branch, commit, subject = parsed

        if branch == "=" and not include_picked:
            continue

        message = git.message(commit)
        yield Commit(
            prnum=extract_prnum(message),
            fixes=extract_fixes(message),
            timestamp=timestamp,
            branch=branch,
            commit=commit,
            subject=shorten(subject),
        )


def format_table(commits: Sequence[Commit], left: str, right: str) -> str:
    lines = [
        "These cherries are hanging on the git-tree:",
        "",
        f"  <-  {left}",
        f"  ->  {right}",
        "  ==  both",
        "",
        " prnum  | fixes  | br |   commit   |   subject",
        "------- | ------ | -- | ---------- | " + "-" * 43,
    ]
    lines.extend(
        " {:>6} | {:>6} | {} | {} | {} ".format(
            f"#{entry.prnum}",
            entry.fixes,
            BRANCH_MARKERS[entry.branch],
            entry.commit,
            entry.subject,
        )
        for entry in commits
    )
    return "".join(f"{line}\n" for line in lines)

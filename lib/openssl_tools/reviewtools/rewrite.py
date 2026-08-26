# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Rewriting the messages of a range of commits.

This is what `git filter-branch --msg-filter` was doing, minus the
generality: replay the range with `git commit-tree`, then move the branch
with `git update-ref`.  Nothing is destroyed -- commit-tree only creates
objects, and the old tip stays in the reflog.

Tags whose target was rewritten are re-pointed, keeping their tagger, date
and message, which is what `--tag-name-filter cat` did.  Tags outside the
range are untouched, by construction: only targets present in the old-to-new
map are considered.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .commands import CommandRunner, run_command
from .errors import ReviewError

#: Record and field separators for reading commits in one pass.  Neither can
#: appear in the fields git substitutes.
_RECORD = "\x1e"
_FIELD = "\x1f"

_FIELDS = (
    "%H",  # sha
    "%T",  # tree
    "%P",  # parents, space separated
    "%an",
    "%ae",
    "%aI",
    "%cn",
    "%ce",
    "%cI",
    "%B",  # raw body, must stay last: it contains newlines
)
_FORMAT = _RECORD + _FIELD.join(_FIELDS)

_TAG_OBJECT_LINE = re.compile(r"^object [0-9a-f]{40,}$", re.MULTILINE)


@dataclass(frozen=True)
class CommitInfo:
    """Everything needed to rebuild a commit with a different message."""

    sha: str
    tree: str
    parents: tuple[str, ...]
    author_name: str
    author_email: str
    author_date: str
    committer_name: str
    committer_email: str
    committer_date: str
    message: str

    @property
    def identity_env(self) -> dict[str, str]:
        """The environment `git commit-tree` reads author and committer from."""
        return {
            "GIT_AUTHOR_NAME": self.author_name,
            "GIT_AUTHOR_EMAIL": self.author_email,
            "GIT_AUTHOR_DATE": self.author_date,
            "GIT_COMMITTER_NAME": self.committer_name,
            "GIT_COMMITTER_EMAIL": self.committer_email,
            "GIT_COMMITTER_DATE": self.committer_date,
        }


def _git(runner: CommandRunner, *args: str, **kwargs: object) -> str:
    completed = runner(["git", *args], capture_output=True, text=True, **kwargs)
    if completed.returncode != 0:
        raise ReviewError(
            f"git {' '.join(args)} failed: "
            + ((completed.stderr or "").strip() or f"exit {completed.returncode}")
        )
    return completed.stdout or ""


def read_range(rev_range: str, *, runner: CommandRunner = run_command) -> list[CommitInfo]:
    """The commits in `rev_range`, oldest first."""
    out = _git(runner, "log", "--reverse", f"--format={_FORMAT}", rev_range)

    commits = []
    for record in out.split(_RECORD):
        if not record.strip():
            continue
        fields = record.split(_FIELD)
        if len(fields) != len(_FIELDS):
            raise ReviewError(f"could not parse commit record: {record!r}")
        sha, tree, parents, an, ae, ad, cn, ce, cd, body = fields
        commits.append(
            CommitInfo(
                sha=sha,
                tree=tree,
                parents=tuple(parents.split()),
                author_name=an,
                author_email=ae,
                author_date=ad,
                committer_name=cn,
                committer_email=ce,
                committer_date=cd,
                # git appends a newline after the format; the body keeps its own.
                message=body.removesuffix("\n"),
            )
        )
    return commits


def current_branch_ref(*, runner: CommandRunner = run_command) -> str:
    """The fully qualified ref HEAD points at."""
    completed = runner(["git", "symbolic-ref", "--quiet", "HEAD"], capture_output=True, text=True)
    if completed.returncode != 0 or not (completed.stdout or "").strip():
        raise ReviewError("HEAD is detached; check out a branch first")
    return completed.stdout.strip()


def replay(
    commits: Sequence[CommitInfo],
    transform: Callable[[CommitInfo], str],
    *,
    runner: CommandRunner = run_command,
) -> dict[str, str]:
    """Rebuild `commits` with transformed messages, returning old -> new.

    The first commit keeps its original parents; each one after is re-parented
    onto what was just built, so the range stays a chain.
    """
    mapping: dict[str, str] = {}

    for commit in commits:
        parents = [mapping.get(parent, parent) for parent in commit.parents]
        args = ["commit-tree", commit.tree]
        for parent in parents:
            args += ["-p", parent]

        message = transform(commit)
        new_sha = _git(
            runner, *args, input=message, env={**_environ(), **commit.identity_env}
        ).strip()
        if not new_sha:
            raise ReviewError(f"commit-tree produced nothing for {commit.sha}")
        mapping[commit.sha] = new_sha

    return mapping


def update_branch(
    ref: str,
    new_tip: str,
    old_tip: str,
    *,
    reason: str = "addrev",
    runner: CommandRunner = run_command,
) -> None:
    """Move `ref` to `new_tip`, failing if it no longer points at `old_tip`."""
    _git(runner, "update-ref", "-m", reason, ref, new_tip, old_tip)


def repoint_tags(mapping: dict[str, str], *, runner: CommandRunner = run_command) -> list[str]:
    """Move any tag whose target was rewritten.  Returns the names moved.

    An annotated tag is rebuilt rather than replaced, so its tagger, date and
    message survive: tag objects are immutable, and `git tag -f` would stamp
    whoever is running this as the tagger.
    """
    if not mapping:
        return []

    # The peeled target comes from the same call: %(*objectname) is the commit
    # an annotated tag points at, and is empty for a lightweight one, where
    # %(objectname) is the commit already.  Asking rev-parse per tag instead
    # costs one subprocess for every tag in the repository -- 443 of them in
    # an openssl clone, on every run, to move at most one.
    listing = _git(
        runner,
        "for-each-ref",
        "--format=%(refname)%09%(objecttype)%09%(objectname)%09%(*objectname)",
        "refs/tags",
    )

    moved = []
    for line in listing.splitlines():
        if not line.strip():
            continue
        refname, objecttype, objectname, peeled = line.split("\t")

        # A tag on a tree or a blob peels to something that is not a commit,
        # so it is simply never in the map.
        new_target = mapping.get(peeled or objectname)
        if new_target is None:
            continue

        if objecttype == "tag":
            raw = _git(runner, "cat-file", "tag", refname)
            rebuilt = _TAG_OBJECT_LINE.sub(f"object {new_target}", raw, count=1)
            new_object = _git(runner, "mktag", input=rebuilt).strip()
            _git(runner, "update-ref", refname, new_object, objectname)
        else:
            _git(runner, "update-ref", refname, new_target, objectname)

        moved.append(refname.removeprefix("refs/tags/"))

    return moved


def _environ() -> dict[str, str]:
    import os

    return dict(os.environ)

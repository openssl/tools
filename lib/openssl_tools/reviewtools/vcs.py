# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The version control systems addrev works on top of.

addrev's pipeline -- resolving reviewers and rewriting commit messages
-- is independent of the version control system underneath; only how
commits are selected, read back and rewritten differs.  That difference
is one class per VCS, behind the `Vcs` interface, so the pipeline in
addrev_cli speaks one vocabulary.
"""

from __future__ import annotations

import abc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import rewrite
from .commands import CommandRunner, run_command


@dataclass(frozen=True)
class Commit:
    """What the message transform needs to know about a commit."""

    id: str
    author_email: str
    message: str


@dataclass(frozen=True)
class RewriteOutcome:
    """The result of rewriting the selected commits.

    Tags are a git concept, so only the git implementation ever reports
    moved ones.
    """

    selected: int
    changed: int
    moved_tags: tuple[str, ...] = ()


class Vcs(abc.ABC):
    """How addrev talks to the version control system of a working copy."""

    def __init__(self, *, runner: CommandRunner = run_command) -> None:
        self._runner = runner

    @abc.abstractmethod
    def default_selection(self, last_n: int | None) -> str:
        """The selection for "the last N commits", or the tip when N is None."""

    @abc.abstractmethod
    def user_email(self) -> str | None:
        """The configured user email address, if there is one."""

    @abc.abstractmethod
    def check_preconditions(self) -> None:
        """Raise ReviewError if the working copy is unsafe to rewrite in."""

    @abc.abstractmethod
    def rewrite_messages(
        self,
        selection: str,
        transform: Callable[[Commit], str],
    ) -> RewriteOutcome:
        """Rewrite the messages of the selected commits through `transform`."""


class Git(Vcs):
    """The git method: replay the selection, then move the branch.

    The plumbing lives in rewrite.py; this is the same flow addrev has
    always had, with tag re-pointing included.
    """

    def default_selection(self, last_n: int | None) -> str:
        return f"HEAD~{last_n}.." if last_n is not None else "HEAD^.."

    def user_email(self) -> str | None:
        completed = self._runner(
            ["git", "config", "--get", "user.email"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return None
        return (completed.stdout or "").strip() or None

    def check_preconditions(self) -> None:
        # There is no branch to move when HEAD is detached;
        # current_branch_ref raises ReviewError in that case.
        rewrite.current_branch_ref(runner=self._runner)

    def rewrite_messages(
        self,
        selection: str,
        transform: Callable[[Commit], str],
    ) -> RewriteOutcome:
        commits = rewrite.read_range(selection, runner=self._runner)
        if not commits:
            return RewriteOutcome(selected=0, changed=0)

        changed = 0

        def transform_info(info: rewrite.CommitInfo) -> str:
            nonlocal changed
            new_message = transform(
                Commit(id=info.sha, author_email=info.author_email, message=info.message)
            )
            if new_message != info.message:
                changed += 1
            return new_message

        ref = rewrite.current_branch_ref(runner=self._runner)
        old_tip = commits[-1].sha
        mapping = rewrite.replay(commits, transform_info, runner=self._runner)
        new_tip = mapping[old_tip]
        if new_tip == old_tip:
            return RewriteOutcome(selected=len(commits), changed=0)
        rewrite.update_branch(ref, new_tip, old_tip, runner=self._runner)
        moved = rewrite.repoint_tags(mapping, runner=self._runner)
        return RewriteOutcome(selected=len(commits), changed=changed, moved_tags=tuple(moved))


def detect(*, runner: CommandRunner = run_command) -> Vcs:
    """The VCS of the current working copy."""
    if Path(".jj").is_dir():
        # Local import: jj.py itself builds on this module.
        from .jj import Jj

        return Jj(runner=runner)
    return Git(runner=runner)

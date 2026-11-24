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
is one class per VCS, each in its own module behind the `Vcs`
interface, so the pipeline in addrev_cli speaks one vocabulary.
"""

from __future__ import annotations

import abc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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


def detect(*, runner: CommandRunner = run_command) -> Vcs:
    """The VCS of the current working copy."""
    # Local imports: the backend modules themselves build on this module.
    if Path(".jj").is_dir():
        from .jj import Jj

        return Jj(runner=runner)

    from .git import Git

    return Git(runner=runner)

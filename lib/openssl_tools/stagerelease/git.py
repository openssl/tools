# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The git operations the staging run needs."""

from __future__ import annotations

import re
from pathlib import Path

from .errors import ReleaseError
from .run import Result, Runner

#: Branches a release may be staged from: master, a 3.0+ release branch, or a
#: pre-3.0 release branch.
RECOGNISED_BRANCHES = (
    re.compile(r"^master$"),
    re.compile(r"^OpenSSL_[0-9]+_[0-9]+_[0-9]+[a-z]*-stable$"),
    re.compile(r"^openssl-[0-9]+\.[0-9]+$"),
)


def is_recognised_branch(name: str) -> bool:
    return any(pattern.match(name) for pattern in RECOGNISED_BRANCHES)


class Git:
    """A worktree, addressed through the git CLI."""

    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    def _git(self, *args: str, check: bool = True) -> Result:
        return self.runner.run(("git", *args), check=check)

    # -- inspection ---------------------------------------------------------

    def toplevel(self) -> Path:
        result = self._git("rev-parse", "--show-toplevel", check=False)
        if not result.ok:
            raise ReleaseError("Not in a git worktree")
        return Path(result.one_line())

    def tracks(self, path: str) -> bool:
        """Whether `path` is tracked in the index."""
        return bool(self._git("ls-files", "--", path).one_line())

    def blob_at_head(self, path: str) -> str:
        """The committed contents of `path`.

        Version data is read from HEAD rather than the worktree, matching the
        shell's `git cat-file blob HEAD:...`.  Staging refuses to run on a
        dirty worktree, so the two agree in practice, but reading the commit
        is what makes that guarantee meaningful.
        """
        return self._git("cat-file", "blob", f"HEAD:{path}").stdout

    def head(self) -> str:
        return self._git("rev-parse", "HEAD").one_line()

    def head_message(self) -> str:
        """The full commit message of HEAD, subject and body."""
        return self._git("log", "-1", "--pretty=%B").stdout

    def user_email(self) -> str | None:
        """The configured author address, or None if git has no opinion."""
        result = self._git("config", "--get", "user.email", check=False)
        return result.one_line() or None

    def current_branch(self) -> str:
        return self._git("rev-parse", "--abbrev-ref", "HEAD").one_line()

    def upstream_or_head(self) -> str:
        """The upstream ref name, falling back to the HEAD commit id."""
        result = self._git("rev-parse", "--abbrev-ref", "@{u}", check=False)
        if result.ok and result.one_line():
            return result.one_line()
        return self.head()

    def push_remote(self) -> str:
        """The remote this branch pushes to."""
        symbolic = self._git("symbolic-ref", "-q", "HEAD", check=False).one_line()
        if not symbolic:
            return ""
        return self._git("for-each-ref", "--format=%(push:remotename)", symbolic).one_line()

    def remote_url(self, remote: str) -> str:
        """The URL of `remote`, or `remote` itself when it is already a URL."""
        if not remote:
            return ""
        result = self._git("remote", "get-url", remote, check=False)
        if result.ok and result.one_line():
            return result.one_line()
        return remote

    def is_clean(self) -> bool:
        """Whether the worktree has no changes at all, untracked included."""
        return not self._git("status", "-s").one_line()

    def has_tracked_changes(self) -> bool:
        """Whether any tracked, non-submodule file differs from HEAD."""
        result = self._git(
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--ignore-submodules=all",
        )
        return bool(result.one_line())

    def modified_paths(self) -> list[str]:
        """Tracked paths that differ from HEAD."""
        result = self._git(
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--ignore-submodules=all",
        )
        return [line[3:] for line in result.lines() if line.strip()]

    def changed_since(self, before: str) -> list[tuple[str, str]]:
        """(status, path) pairs for commits made since `before`.

        `before` is a date understood by `git rev-list --before`.  Used by the
        copyright pass to find files touched during the current year.
        """
        start = self._git("rev-list", "-1", f"--before={before}", "HEAD", check=False).one_line()
        if not start:
            return []
        result = self._git("diff-tree", "-r", "--name-status", f"{start}..HEAD")
        pairs: list[tuple[str, str]] = []
        for line in result.lines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0].strip()
            # Deletions have nothing left to rewrite.
            if status.startswith("D"):
                continue
            # Renames and copies report the destination last.
            pairs.append((status, parts[-1]))
        return pairs

    # -- mutation -----------------------------------------------------------

    def add_update(self) -> None:
        """Stage modifications to tracked files."""
        self._git("add", "-u")

    def add(self, path: str) -> None:
        self._git("add", "--", path)

    def commit(self, message: str) -> None:
        self._git("commit", "-m", message)

    def amend_message(self, message: str) -> None:
        """Replace HEAD's message, keeping its author and its tree.

        `--cleanup=verbatim` because the message has already been assembled
        exactly as it should be stored; git's default would strip trailing
        whitespace and could disturb the trailer block.
        """
        self._git("commit", "--amend", "--cleanup=verbatim", "-m", message)

    def tag(self, name: str, message: str) -> None:
        """Create an annotated tag.

        Never signed: the release key lives on an HSM the build host cannot
        reach, so the tag is re-signed later, where that access exists.
        """
        self._git("tag", "-a", name, "-m", message)

    def create_branch(self, name: str) -> None:
        self._git("checkout", "-b", name)

    def checkout_branch(self, name: str) -> None:
        self._git("checkout", name)

    def restore_worktree_to(self, rev: str) -> None:
        """Put every tracked file back to its contents at `rev`, leaving HEAD.

        This is the shell's `git reset HEAD^ -- . && git checkout -- .`: it
        gives the post-release fixups the same starting point the release
        fixups had, without the artifacts `git revert` would leave behind.
        """
        self._git("reset", "-q", rev, "--", ".")
        self._git("checkout", "--", ".")

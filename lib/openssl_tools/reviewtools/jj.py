# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The jj method: rewrite commit descriptions with 'jj describe'.

In a jj repo there is no branch to move and no tags to chase: describing
a commit rewrites it and rebases its descendants in one go.  Change ids
stay stable across those rewrites, so each selected commit is addressed
by its change id while the descriptions are replaced one by one.
"""

from __future__ import annotations

from collections.abc import Callable

from .errors import ReviewError
from .vcs import Commit, RewriteOutcome, Vcs

#: Record and field separators for reading commits in one pass, like
#: rewrite.py does on the git side.  The template spells them as jj
#: string escapes, so the backslashes are doubled here.
_RECORD = "\x1e"
_FIELD = "\x1f"

_TEMPLATE = (
    'change_id ++ "\\x1f"'
    ' ++ commit_id ++ "\\x1f"'
    ' ++ author.email() ++ "\\x1f"'
    # The description must stay last: it contains newlines.
    ' ++ description ++ "\\x1e"'
)


class Jj(Vcs):
    def default_selection(self, last_n: int | None) -> str:
        # @- is the jj counterpart of HEAD: the parent of the
        # working-copy commit.
        return f"ancestors(@-, {last_n})" if last_n is not None else "@-"

    def user_email(self) -> str | None:
        completed = self._runner(
            ["jj", "config", "get", "user.email"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return None
        return (completed.stdout or "").strip() or None

    def check_preconditions(self) -> None:
        # Rewriting descriptions underneath a working copy that holds
        # in-flight changes, or that is not at the tip of history, is a
        # recipe for clobbering work the user has in progress.
        state = self._jj(
            "log", "--no-graph", "-r", "@", "-T", 'if(empty, "empty", "nonempty")'
        ).strip()
        if state != "empty":
            raise ReviewError("refusing to work: the working-copy commit @ is not empty")
        children = self._jj("log", "--no-graph", "-r", "children(@)")
        if children.strip():
            raise ReviewError(
                "refusing to work: the working-copy commit @ has children (is not the tip)"
            )

    def rewrite_messages(
        self,
        selection: str,
        transform: Callable[[Commit], str],
    ) -> RewriteOutcome:
        selected = self._read_revset(selection)
        changed = 0
        for change_id, commit in selected:
            new_message = transform(commit)
            if new_message != commit.message:
                self._jj("describe", "--stdin", change_id, input=new_message)
                changed += 1
        return RewriteOutcome(selected=len(selected), changed=changed)

    def _jj(self, *args: str, **kwargs: object) -> str:
        completed = self._runner(["jj", *args], capture_output=True, text=True, **kwargs)
        if completed.returncode != 0:
            raise ReviewError(
                f"jj {' '.join(args)} failed: "
                + ((completed.stderr or "").strip() or f"exit {completed.returncode}")
            )
        return completed.stdout or ""

    def _read_revset(self, revset: str) -> list[tuple[str, Commit]]:
        """The commits `revset` resolves to, each paired with its change id."""
        out = self._jj("log", "--no-graph", "-r", revset, "-T", _TEMPLATE)

        commits = []
        for record in out.split(_RECORD):
            # jj ends each template output with a newline, which lands at
            # the start of the following record.
            record = record.lstrip("\n")
            if not record.strip():
                continue
            fields = record.split(_FIELD)
            if len(fields) != 4:
                raise ReviewError(f"could not parse jj log record: {record!r}")
            change_id, commit_id, email, description = fields
            commits.append(
                (
                    change_id,
                    Commit(
                        id=commit_id,
                        author_email=email,
                        message=description.removesuffix("\n"),
                    ),
                )
            )
        return commits

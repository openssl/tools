# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The one exception type this tool raises on expected failures.

Anything that the operator could plausibly hit -- a dirty worktree, an
impossible release transition, an unrecognised branch -- is a ReleaseError.
The CLI catches it, prints the message to stderr and exits 1, so a stack
trace only ever means a genuine bug.
"""

from __future__ import annotations


class ReleaseError(Exception):
    """An expected, operator-facing failure."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\n{self.hint}"
        return self.message

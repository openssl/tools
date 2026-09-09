# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The shape of the command runner these tools accept.

`subprocess.run` satisfies `CommandRunner`, and so does a test double that
records invocations instead of making them.  Spelling it out as a Protocol
rather than leaving the parameter untyped is what lets a substitute be
checked against the real interface.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from typing import Any, Protocol


class CompletedCommand(Protocol):
    """What a runner reports back.

    `stdout` is Any because subprocess.CompletedProcess is generic over it:
    str under text=True, bytes otherwise.
    """

    returncode: int
    stdout: Any
    stderr: Any


class CommandRunner(Protocol):
    """Runs a command and returns its outcome.

    The argv parameter is positional-only, because callers pass it
    positionally and `subprocess.run` names it `args`.
    """

    def __call__(self, argv: Sequence[str], /, **kwargs: Any) -> CompletedCommand: ...


def run_command(argv: Sequence[str], /, **kwargs: Any) -> CompletedCommand:
    """The default runner.

    A thin adapter rather than `subprocess.run` itself: that function is
    overloaded, and mypy cannot show an overloaded function satisfies a
    Protocol.  It is also the one place to pin `check=False` -- every caller
    here inspects `returncode` and reports failures itself.
    """
    kwargs.setdefault("check", False)
    return subprocess.run(argv, **kwargs)  # noqa: S603

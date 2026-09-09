# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Running external commands.

Everything this tool shells out to goes through `Runner`, so that the parts
of the code that make decisions can be tested against a fake.  The shell
version had no such seam: `./Configure`, `make` and `git` were called inline
from the middle of the logic, which is why none of it could be tested.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ReleaseError


@dataclass
class Result:
    """The outcome of one external command."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def lines(self) -> list[str]:
        return self.stdout.splitlines()

    def one_line(self) -> str:
        return self.stdout.strip()


@dataclass
class Runner:
    """Runs commands in a working directory, reporting output to a logger.

    `log` receives each line of a command's output, so --verbose can show
    the progress of a long `make` without this class knowing anything about
    verbosity levels.
    """

    cwd: Path
    log: Callable[[str], None] = lambda line: None
    #: Recorded for debugging and for the tests to assert against.
    history: list[tuple[str, ...]] = field(default_factory=list)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
        echo_output: bool = False,
    ) -> Result:
        """Run `argv` and return its result.

        Output is always captured (stderr folded into stdout) so a failure
        message can be included in the exception.  With `echo_output` each
        line is also handed to `log` as it is read, which is how the noisy
        build steps stay visible under --verbose.
        """
        argv = tuple(str(a) for a in argv)
        self.history.append(argv)

        full_env = None
        if env is not None:
            import os

            full_env = {**os.environ, **env}

        # argv is always a list and shell is never used, so nothing here
        # goes through a shell parser.
        proc = subprocess.Popen(  # noqa: S603
            argv,
            cwd=str(cwd or self.cwd),
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )

        chunks: list[str] = []
        # Always a pipe, because stdout=PIPE above; the guard is for type
        # checkers rather than for a case that can happen.
        if proc.stdout is not None:
            for line in proc.stdout:
                chunks.append(line)
                if echo_output:
                    self.log(f"> {line.rstrip()}")
        proc.wait()

        result = Result(argv=argv, returncode=proc.returncode, stdout="".join(chunks))
        if check and not result.ok:
            raise ReleaseError(
                "Command failed ({}): {}".format(result.returncode, " ".join(argv)),
                result.stdout.strip() or None,
            )
        return result

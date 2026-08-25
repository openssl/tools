# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Driving the OpenSSL build system during staging.

Kept behind a class so the orchestration can be tested without configuring
and building OpenSSL, which is what made the shell version untestable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from .run import Runner


class BuildSystem(Protocol):
    """The build steps a staging run drives.

    Stated as a Protocol because the point of this module is that stage.py
    can be tested against a stub -- so the stub has to be a legitimate
    substitute, not merely duck-typed past the checker.
    """

    def configure(self) -> None: ...
    def update(self, *, is_alpha: bool) -> None: ...


class Build:
    """The `./Configure` and `make` steps a release needs."""

    def __init__(self, runner: Runner, source_dir: Path) -> None:
        self.runner = runner
        self.source_dir = source_dir

    def has_make_target(self, target: str) -> bool:
        """Whether the generated Makefile defines `target`.

        Not every branch has `renumber` or `update-fips-checksums`, so their
        absence is normal rather than an error.
        """
        makefile = self.source_dir / "Makefile"
        if not makefile.is_file():
            return False
        pattern = re.compile(rf"^{re.escape(target)} *:", re.MULTILINE)
        return bool(pattern.search(makefile.read_text(errors="replace")))

    def configure(self) -> None:
        self.runner.run(["./Configure", "cc"], echo_output=True)

    def update(self, *, is_alpha: bool) -> None:
        """Run `make update`, plus the checks a non-alpha release requires."""
        self.runner.run(["make", "update"], echo_output=True)

        # An alpha may still have symbols without assigned ordinal numbers;
        # a beta or final release may not.
        if not is_alpha and self.has_make_target("renumber"):
            self.runner.run(["make", "renumber"], echo_output=True)

        if self.has_make_target("update-fips-checksums"):
            self.runner.run(["make", "clean"], echo_output=True)
            self.runner.run(["make", "update-fips-checksums"], echo_output=True)

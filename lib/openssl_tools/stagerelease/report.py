# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Progress output at three levels of noisiness.

Replaces the shell's $ECHO / $VERBOSE / $DEBUG variables, which held either
`echo` or `:` and were invoked as commands.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TextIO


@dataclass
class Reporter:
    quiet: bool = False
    verbose_enabled: bool = False
    debug_enabled: bool = False
    stream: TextIO = field(default_factory=lambda: sys.stdout)
    error_stream: TextIO = field(default_factory=lambda: sys.stderr)

    def echo(self, message: str) -> None:
        """Ordinary progress, silenced by --quiet."""
        if not self.quiet:
            print(message, file=self.stream)

    def verbose(self, message: str) -> None:
        """Detail, shown only under --verbose."""
        if self.verbose_enabled and not self.quiet:
            print(message, file=self.stream)

    def debug(self, message: str) -> None:
        """Internal state, shown only under --debug, always on stderr."""
        if self.debug_enabled:
            print(f"DEBUG: {message}", file=self.error_stream)

    def out(self, message: str) -> None:
        """Final results, never silenced."""
        print(message, file=self.stream)

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Bring copyright years up to date -- a port of do-copyright-year.

Every source file touched since the start of the current year has the end
year of its OpenSSL copyright notice extended to this year.  A notice that
already names a single year becomes a range, and a range that would collapse
to one year (2026-2026) is written as that year alone.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from .textutil import read_text, split_lines, write_text

COPYRIGHT_OWNER = "The OpenSSL Project"

_SOME_YEAR = r"[12][0-9][0-9][0-9]"
_YEAR_RANGE = re.compile(rf"({_SOME_YEAR})(-{_SOME_YEAR})?")
_REPEATED_YEAR = re.compile(rf"({_SOME_YEAR})-\1")
_COPYRIGHT = re.compile(rf"Copyright .*{_SOME_YEAR}(-{_SOME_YEAR})? .*{COPYRIGHT_OWNER}")

#: Always refreshed, whether or not they were touched this year.
ALWAYS_CONSIDER = ("README.md", "README")


def update_line(line: str, this_year: int) -> str:
    """Extend the copyright year range on one line, if it carries a notice."""
    if not _COPYRIGHT.search(line):
        return line
    line = _YEAR_RANGE.sub(lambda m: f"{m[1]}-{this_year}", line, count=1)
    return _REPEATED_YEAR.sub(r"\1", line, count=1)


def update_text(text: str, this_year: int) -> str:
    return "".join(update_line(line, this_year) for line in split_lines(text))


class ChangedSince(Protocol):
    """The slice of the git interface this pass needs."""

    def changed_since(self, before: str) -> list[tuple[str, str]]: ...
    def add(self, path: str) -> None: ...


@dataclass
class CopyrightResult:
    considered: int
    updated: list[str]


def update_copyright_years(
    git: ChangedSince,
    root: Path,
    today: date,
    log: Callable[[str], None] = lambda line: None,
) -> CopyrightResult:
    """Update and stage copyright years across files touched this year.

    Returns how many files were examined and which ones changed.  Files are
    only written when their contents actually differ, so unchanged files keep
    their mtime -- the shell achieved the same thing by rewriting a copy and
    comparing before moving it back.
    """
    new_year_day = f"{today.year}-01-01"

    candidates: list[str] = [path for _, path in git.changed_since(new_year_day)]
    candidates.extend(name for name in ALWAYS_CONSIDER if (root / name).is_file())

    considered = 0
    updated: list[str] = []
    seen: set[str] = set()

    for relative in candidates:
        if relative in seen:
            continue
        seen.add(relative)

        path = root / relative
        if not path.is_file():
            # Directories, submodules, and paths removed since the commit
            # that mentioned them.
            continue
        considered += 1

        text = read_text(path)
        new_text = update_text(text, today.year)
        if new_text == text:
            continue

        write_text(path, new_text)
        git.add(relative)
        updated.append(relative)
        log(f"> {relative}")

    return CopyrightResult(considered=considered, updated=updated)

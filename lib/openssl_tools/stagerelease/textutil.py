# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Line handling and file I/O shared by the text-rewriting passes."""
from __future__ import annotations

from pathlib import Path


def split_lines(text: str) -> list[str]:
    """Split `text` on newlines, keeping each terminator.

    `str.splitlines()` is not usable here: it also breaks on form feeds and
    several Unicode separators, which appear in OpenSSL's older C sources and
    would be silently rewritten into plain newlines when the lines were
    rejoined.  Splitting on '\\n' alone round-trips any input exactly.
    """
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def read_text(path: Path) -> str:
    """Read a file without altering line endings or choking on odd bytes.

    Undecodable bytes become surrogates and are written back unchanged by
    `write_text`, so a pass over a file with mixed encodings is lossless.
    """
    with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        return fh.read()


def write_text(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write(text)

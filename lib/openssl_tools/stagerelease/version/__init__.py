# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Versioning schemes and detection."""
from __future__ import annotations

from typing import Protocol

from ..errors import ReleaseError
from .base import BUMP_KINDS, Patch, ReleaseState, Scheme
from .legacy import LegacyScheme, decode_patch, encode_patch
from .modern import ModernScheme

__all__ = [
    "BUMP_KINDS",
    "LegacyScheme",
    "ModernScheme",
    "Patch",
    "ReleaseState",
    "Scheme",
    "decode_patch",
    "detect_scheme",
    "encode_patch",
]

#: Candidate version files, most recent scheme first.  OpenSSL 3.0 and on use
#: VERSION.dat, 1.1.y use include/openssl/opensslv.h, and 1.0.y (as well as
#: 0.x.y) use crypto/opensslv.h.
VERSION_FILES = ("VERSION.dat", "include/openssl/opensslv.h", "crypto/opensslv.h")


class TracksFiles(Protocol):
    """The slice of the git interface that detection needs."""

    def tracks(self, path: str) -> bool: ...


def detect_scheme(git: TracksFiles) -> Scheme:
    """Work out which versioning scheme the worktree uses.

    Raises ReleaseError when none of the known version files is tracked,
    which is how a worktree that is not an OpenSSL checkout gets rejected.
    """
    for candidate in VERSION_FILES:
        if not git.tracks(candidate):
            continue
        if candidate == "VERSION.dat":
            return ModernScheme()
        return LegacyScheme(candidate, has_spec=git.tracks("openssl.spec"))

    raise ReleaseError(
        "Couldn't find OpenSSL version data",
        "Looked for: " + ", ".join(VERSION_FILES),
    )

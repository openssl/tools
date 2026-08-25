# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The pre-3.0 OpenSSL versioning scheme, stored in an opensslv.h header.

The version lives in a packed hex macro:

    #define OPENSSL_VERSION_NUMBER 0xMNNFFPPSL

M = major, NN = minor, FF = fix, PP = patch, S = state.  S is 0 for a
development tree and 0xf for a release; the values 1..e denoted betas 1..14
under a release process that predates this tool, and are not produced here.

PP is a number, but the version is written with a letter chain -- 1.0.2 is
PP=0, 1.0.2a is PP=1, 1.0.2y is PP=25, 1.0.2za is PP=26.  See `encode_patch`.

All 1.x branches are end-of-life; this exists so the tool can still read and
tag an old branch, not because new 1.x releases are expected.
"""
from __future__ import annotations

import re
from dataclasses import replace

from ..errors import ReleaseError
from .base import Patch, ReleaseState, Scheme

_VERSION_NUMBER_RE = re.compile(
    r"^[ \t]*#[ \t]*define[ \t]+OPENSSL_VERSION_NUMBER[ \t]+"
    r"0x([0-9a-fA-F])([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F])L$",
    re.MULTILINE,
)

_SUB_VERSION_NUMBER_RE = re.compile(
    r"^([ \t]*#[ \t]*define[ \t]+OPENSSL_VERSION_NUMBER[ \t]+0x)[0-9a-fA-F]+L$",
    re.MULTILINE,
)

_SUB_VERSION_TEXT_RE = re.compile(
    r"^([ \t]*#[ \t]*define[ \t]+OPENSSL_VERSION_TEXT[ \t]+)"
    r'"OpenSSL \d+\.\d+\.\dz*[a-y]?(-fips)?(-dev)?  [^"]+"$',
    re.MULTILINE,
)

_SUB_SHLIB_RE = re.compile(
    r'^([ \t]*#[ \t]*define[ \t]+SHLIB_VERSION_NUMBER[ \t]+)"[^"]*"$',
    re.MULTILINE,
)

_PATCH_RE = re.compile(r"^(z*)([a-y]?)$")


def decode_patch(patch: str) -> int:
    """Turn a patch letter chain into its PP number.

    Inverse of `encode_patch`.  The shell's set_version() got this wrong for
    chains of more than one 'z': its regex `^(z)*(.)$` captured only the last
    repetition, so it read every chain as having a single 'z'.  1.0.2 never
    got past 'zh', so the bug was never reachable, but there is no reason to
    carry it forward.
    """
    match = _PATCH_RE.match(patch)
    if not match:
        raise ReleaseError(f"Not a valid patch level: {patch!r}")
    zs, letter = match.groups()
    return len(zs) * 25 + (ord(letter) - ord("a") + 1 if letter else 0)


def encode_patch(number: int) -> str:
    """Turn a PP number into its patch letter chain."""
    if number < 0:
        raise ReleaseError(f"Not a valid patch number: {number}")
    zs = 0
    while number > 25:
        zs += 1
        number -= 25
    return "z" * zs + (chr(number + ord("a") - 1) if number > 0 else "")


class LegacyScheme(Scheme):
    """MAJOR.MINOR.FIX plus a patch letter, as used before OpenSSL 3.0."""

    def __init__(self, version_file: str, has_spec: bool) -> None:
        # 1.0.x ships an openssl.spec that carries the version too; 1.1.x
        # does not.
        files = ("README", "CHANGES", "NEWS")
        if has_spec:
            files += ("openssl.spec",)
        super().__init__(release_files=files)
        self.version_file = version_file

    def parse(self, text: str) -> ReleaseState:
        match = _VERSION_NUMBER_RE.search(text)
        if not match:
            raise ReleaseError(
                f"No OPENSSL_VERSION_NUMBER definition found in {self.version_file}"
            )

        major = int(match.group(1), 16)
        minor = int(match.group(2), 16)
        fix = int(match.group(3), 16)
        patch = encode_patch(int(match.group(4), 16))
        dev = int(match.group(5), 16) == 0

        return ReleaseState(
            major=major,
            minor=minor,
            patch=patch,
            fix=fix,
            # The shell parsed SHLIB_VERSION_NUMBER out of the header and then
            # immediately overwrote it with this, so only this value ever had
            # any effect.
            shlib_version=(
                f"{major}.{minor}.0" if minor == 0 else f"{major}.{minor}"
            ),
            dev=dev,
            pre_label="",
            pre_num=0,
        )

    def render(self, state: ReleaseState, current: str) -> str:
        number = "{:x}{:02x}{:02x}{:02x}{:x}".format(
            state.major,
            state.minor,
            state.fix or 0,
            decode_patch(str(state.patch)),
            0 if state.dev else 0xF,
        )
        text = "{}.{}.{}{}".format(
            state.major, state.minor, state.fix or 0, state.patch
        )
        release_date = state.release_date or "xx XXX xxxx"
        tag = state.marked_pre_release_tag

        # Every matching line is rewritten, not just the first.  The Perl this
        # replaces ran under `perl -pi`, which applied each substitution once
        # per line, and the headers define OPENSSL_VERSION_TEXT twice -- once
        # inside `#ifdef OPENSSL_FIPS` and once outside.  Both must move.
        result = _SUB_VERSION_NUMBER_RE.sub(
            lambda m: f"{m.group(1)}{number}L", current
        )
        result = _SUB_VERSION_TEXT_RE.sub(
            # Group 2 is an optional '-fips' marker, which is preserved.  The
            # header's own '-dev' marker (group 3) is dropped and replaced by
            # whatever tag the new state calls for.
            lambda m: '{}"OpenSSL {}{}{}  {}"'.format(
                m.group(1), text, m.group(2) or "", tag, release_date
            ),
            result,
        )
        result = _SUB_SHLIB_RE.sub(
            lambda m: f'{m.group(1)}"{state.shlib_version}"', result
        )
        return result

    def series(self, state: ReleaseState) -> str:
        return f"{state.major}.{state.minor}.{state.fix or 0}"

    def version(self, state: ReleaseState) -> str:
        return f"{self.series(state)}{state.patch}"

    def full_version(self, state: ReleaseState) -> str:
        # No build metadata under this scheme.
        return self.version(state) + state.marked_pre_release_tag

    def branch_name(self, state: ReleaseState) -> str:
        return "OpenSSL_{}-stable".format(self.series(state).replace(".", "_"))

    def tag_name(self, state: ReleaseState) -> str:
        return "OpenSSL_{}".format(self.version(state).replace(".", "_"))

    def next_patch(self, patch: Patch) -> Patch:
        return encode_patch(decode_patch(str(patch)) + 1)

    def next_minor(self, state: ReleaseState) -> ReleaseState:
        # A minor release steps FIX and restarts the patch letters.
        return replace(state, fix=(state.fix or 0) + 1, patch="")

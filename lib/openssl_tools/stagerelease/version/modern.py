# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The OpenSSL 3.0+ versioning scheme, stored in VERSION.dat."""

from __future__ import annotations

import re
from dataclasses import replace

from ..errors import ReleaseError
from .base import Patch, ReleaseState, Scheme

#: 'alpha3', 'beta1-dev', and so on.
_PRE_TAG_RE = re.compile(r"^(?P<label>alpha|beta)(?P<num>\d+)(?P<dev>-dev)?$")

_ASSIGNMENT_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_assignments(text: str) -> dict[str, str]:
    """Read VERSION.dat's KEY=VALUE lines.

    The shell ran this file through `eval`, which meant any shell syntax in
    the file was executed and every assignment leaked into the caller's global
    namespace.  A plain parser is equivalent for well-formed input and cannot
    do anything surprising with malformed input.
    """
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ASSIGNMENT_RE.match(line)
        if match:
            values[match.group("key")] = _unquote(match.group("value"))
    return values


class ModernScheme(Scheme):
    """MAJOR.MINOR.PATCH with a separate pre-release tag, as of OpenSSL 3.0."""

    version_file = "VERSION.dat"

    def __init__(self) -> None:
        super().__init__(release_files=("CHANGES.md", "NEWS.md"))

    def parse(self, text: str) -> ReleaseState:
        values = parse_assignments(text)

        missing = [k for k in ("MAJOR", "MINOR", "PATCH") if k not in values]
        if missing:
            raise ReleaseError(f"{self.version_file} is missing {', '.join(missing)}")

        try:
            major = int(values["MAJOR"])
            minor = int(values["MINOR"])
            patch = int(values["PATCH"])
        except ValueError as exc:
            raise ReleaseError(f"{self.version_file} has a non-numeric version: {exc}") from exc

        dev, pre_label, pre_num = self._parse_pre_release_tag(values.get("PRE_RELEASE_TAG", ""))

        return ReleaseState(
            major=major,
            minor=minor,
            patch=patch,
            build_metadata=values.get("BUILD_METADATA", ""),
            release_date=values.get("RELEASE_DATE", ""),
            shlib_version=values.get("SHLIB_VERSION", ""),
            dev=dev,
            pre_label=pre_label,
            pre_num=pre_num,
        )

    def _parse_pre_release_tag(self, tag: str) -> tuple[bool, str, int | None]:
        if tag == "":
            # A released tree.  pre_num stays None, matching the shell where
            # PRE_NUM came out empty rather than zero for this case.
            return False, "", None
        if tag == "dev":
            return True, "", 0
        match = _PRE_TAG_RE.match(tag)
        if match:
            return (
                match.group("dev") is not None,
                match.group("label"),
                int(match.group("num")),
            )
        raise ReleaseError(
            f"Unrecognised PRE_RELEASE_TAG in {self.version_file}: {tag!r}",
            "Expected '', 'dev', 'alphaN', 'alphaN-dev', 'betaN' or 'betaN-dev'.",
        )

    def render(self, state: ReleaseState, current: str) -> str:
        # The whole file is rewritten from the state, exactly as the shell's
        # set_version() did.  Any key not listed here is dropped.
        return (
            f"MAJOR={state.major}\n"
            f"MINOR={state.minor}\n"
            f"PATCH={state.patch}\n"
            f"PRE_RELEASE_TAG={state.pre_release_tag}\n"
            f"BUILD_METADATA={state.build_metadata}\n"
            f'RELEASE_DATE="{state.release_date}"\n'
            f"SHLIB_VERSION={state.shlib_version}\n"
        )

    def series(self, state: ReleaseState) -> str:
        return f"{state.major}.{state.minor}"

    def version(self, state: ReleaseState) -> str:
        return f"{state.major}.{state.minor}.{state.patch}"

    def full_version(self, state: ReleaseState) -> str:
        return self.version(state) + state.marked_pre_release_tag + state.marked_build_metadata

    def branch_name(self, state: ReleaseState) -> str:
        return f"openssl-{self.series(state)}"

    def tag_name(self, state: ReleaseState) -> str:
        return f"openssl-{self.full_version(state)}"

    def next_patch(self, patch: Patch) -> Patch:
        return int(patch) + 1

    def next_minor(self, state: ReleaseState) -> ReleaseState:
        return replace(state, minor=state.minor + 1, patch=0)

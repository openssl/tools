# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Version state and the scheme interface.

This replaces release-aux/release-version-fn.sh, which kept eighteen shell
globals and dispatched on $VERSION_FILE in five separate functions.  Here the
state is one immutable value object and each versioning scheme is a class.

`ReleaseState` holds only what is actually stored in (or directly implied by)
the version file.  Everything else -- series, version, full_version, the
pre-release tag -- is derived by the scheme, because the derivation differs
between OpenSSL 1.x and 3.0+.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, replace
from typing import Union

# `patch` is an int under the 3.0+ scheme (3.2.1) and a letter chain under the
# 1.x scheme (1.0.2zh), so it has to be one or the other depending on scheme.
Patch = Union[int, str]

#: The transitions `bump()` understands, matching the shell's fixup_version().
BUMP_KINDS = ("alpha", "beta", "final", "minor", "")


@dataclass(frozen=True)
class ReleaseState:
    """The version and release state of a worktree.

    `dev` models the shell's $TYPE, which only ever held '' or 'dev'.

    `pre_num` is None in a released state, mirroring the shell where PRE_NUM
    came out empty for an empty PRE_RELEASE_TAG.  It matters because the
    metadata file and the release text distinguish "no pre-release" from
    "pre-release number 0".
    """

    major: int
    minor: int
    patch: Patch
    fix: int | None = None
    build_metadata: str = ""
    release_date: str = ""
    shlib_version: str = ""
    dev: bool = False
    pre_label: str = ""
    pre_num: int | None = None

    @property
    def type(self) -> str:
        """The shell's $TYPE."""
        return "dev" if self.dev else ""

    @property
    def pre_release_tag(self) -> str:
        """The shell's $PRE_RELEASE_TAG, recomputed from the state.

        Mirrors the `case "$TYPE+$PRE_LABEL+$PRE_NUM"` block: with no
        pre-release label the tag is just the type.
        """
        if not self.pre_label:
            return self.type
        if self.dev:
            return f"{self.pre_label}{self.pre_num or 0}-dev"
        return f"{self.pre_label}{self.pre_num or 0}"

    @property
    def marked_pre_release_tag(self) -> str:
        """The shell's $_PRE_RELEASE_TAG -- the tag with its leading dash."""
        tag = self.pre_release_tag
        return f"-{tag}" if tag else ""

    @property
    def marked_build_metadata(self) -> str:
        """The shell's $_BUILD_METADATA -- the metadata with its leading plus."""
        return f"+{self.build_metadata}" if self.build_metadata else ""

    @property
    def phase(self) -> str:
        """The shell's $before -- "$PRE_LABEL$TYPE".

        One of '', 'dev', 'alpha', 'alphadev', 'beta', 'betadev'.  This is the
        left-hand side of the state machine in state.py.
        """
        return f"{self.pre_label}{self.type}"


class Scheme(abc.ABC):
    """How one OpenSSL versioning scheme reads, derives and writes versions."""

    #: Path of the version file, relative to the worktree root.
    version_file: str

    def __init__(self, release_files: tuple[str, ...]) -> None:
        #: Files needing a fixup pass during release and post-release.
        self.release_files = release_files

    # -- reading and writing ------------------------------------------------

    @abc.abstractmethod
    def parse(self, text: str) -> ReleaseState:
        """Build a ReleaseState from the version file's contents."""

    @abc.abstractmethod
    def render(self, state: ReleaseState, current: str) -> str:
        """Return the new version file contents for `state`.

        `current` is the file's present contents.  The 3.0+ scheme rewrites
        the file wholesale and ignores it; the 1.x scheme has to patch three
        #defines in place and leave the rest of the header alone.
        """

    # -- derived values -----------------------------------------------------

    @abc.abstractmethod
    def series(self, state: ReleaseState) -> str:
        """The release series, e.g. '3.2' or '1.0.2'."""

    @abc.abstractmethod
    def version(self, state: ReleaseState) -> str:
        """The plain version number, e.g. '3.2.1' or '1.0.2zh'."""

    @abc.abstractmethod
    def full_version(self, state: ReleaseState) -> str:
        """The version with pre-release tag and build metadata attached."""

    @abc.abstractmethod
    def branch_name(self, state: ReleaseState) -> str:
        """The standard release branch name for this state."""

    @abc.abstractmethod
    def tag_name(self, state: ReleaseState) -> str:
        """The standard release tag name for this state."""

    # -- transitions --------------------------------------------------------

    @abc.abstractmethod
    def next_patch(self, patch: Patch) -> Patch:
        """The patch level following `patch`."""

    @abc.abstractmethod
    def next_minor(self, state: ReleaseState) -> ReleaseState:
        """Move `state` on to the next minor version, resetting the patch."""

    def bump(self, state: ReleaseState, kind: str) -> ReleaseState:
        """The shell's fixup_version().

        Only advances a counter when the worktree is in development; going
        from a released state to a pre-release state is the state machine's
        job, not this function's.
        """
        if kind not in BUMP_KINDS:
            raise ValueError(f"unknown bump kind: {kind!r}")

        if kind in ("alpha", "beta"):
            if kind != state.pre_label:
                return replace(state, pre_label=kind, pre_num=1)
            if state.dev:
                return replace(state, pre_num=(state.pre_num or 0) + 1)
            return state

        if kind == "minor":
            if state.dev:
                state = self.next_minor(state)
            return replace(state, pre_label="", pre_num=0)

        # 'final' and '' behave identically: leave any pre-release series and
        # step the patch level, but only when coming from development.
        if state.dev:
            state = replace(state, patch=self.next_patch(state.patch))
        return replace(state, pre_label="", pre_num=0)

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Per-file edits applied for the release and post-release commits.

A port of the twelve `release-aux/fixup-*.pl` scripts, which were run as
`perl -pi <script> <file>` with their parameters passed in the environment.
Each is now a function from text to text, which is what makes them testable.

Two conventions carried over from the Perl:

- Only the *first* matching line is ever touched (the `$count-- > 0` idiom).
- The release fixups keep whatever followed the match on that line (Perl's
  `$'`); the post-release fixups replace the line outright and discard it.

Both filename conventions are handled: pre-3.0 OpenSSL uses CHANGES/NEWS,
3.0 and later use CHANGES.md/NEWS.md.  They are not interchangeable.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .textutil import split_lines

RELEASE = "release"
POSTRELEASE = "postrelease"

#: Matches a 3.0+ pre-release version such as '3.2.0-alpha1'.
_PRE_RELEASE_RE = re.compile(r"^\d+\.\d+\.\d+-(?:alpha|beta)")

_CHANGES_RE = re.compile(r"^ Changes between (\S+) and (\S+) \[xx XXX xxxx\]")
_CHANGES_MD_RE = re.compile(r"^### Changes between (\S+) and (\S+) \[xx XXX xxxx\]")
_NEWS_RE = re.compile(
    r"^  Major changes between OpenSSL (\S+) and OpenSSL (\S+) \[under development\]"
)
_NEWS_MD_RE = re.compile(
    r"^### Major changes between OpenSSL (\S+) and OpenSSL (\S+) \[under development\]"
)
_README_RE = re.compile(r"^ OpenSSL.*$")
_SPEC_RE = re.compile(r"^Version:\s+(\S+)$")


@dataclass(frozen=True)
class FixupContext:
    """The parameters the Perl scripts took from the environment."""

    release: str = ""
    release_text: str = ""
    release_date: str = ""
    prev_release_text: str = ""
    prev_release_date: str = ""

    @property
    def is_pre_release(self) -> bool:
        """Whether RELEASE names an alpha or beta, ignoring any -dev marker."""
        return bool(_PRE_RELEASE_RE.match(self.release.replace("-dev", "")))


Fixup = Callable[[str, FixupContext], str]


def _edit_first_match(
    text: str,
    pattern: re.Pattern[str],
    build: Callable[[re.Match[str], str], str | None],
) -> str:
    """Rewrite the first line matching `pattern`.

    `build` receives the match and the rest of that line (Perl's POSTMATCH,
    which for these anchored patterns is the trailing newline plus anything
    after the matched prefix).  Returning None leaves the line alone but
    still counts as the one match, mirroring the Perl.
    """
    lines = split_lines(text)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        replacement = build(match, line[match.end() :])
        if replacement is not None:
            lines[index] = replacement
        break
    return "".join(lines)


# -- release fixups ---------------------------------------------------------


def changes_release(text: str, ctx: FixupContext) -> str:
    return _edit_first_match(
        text,
        _CHANGES_RE,
        lambda m, post: (
            f" Changes between {m[1]} and {ctx.release_text} [{ctx.release_date}]{post}"
        ),
    )


def changes_md_release(text: str, ctx: FixupContext) -> str:
    return _edit_first_match(
        text,
        _CHANGES_MD_RE,
        lambda m, post: (
            f"### Changes between {m[1]} and {ctx.release_text} [{ctx.release_date}]{post}"
        ),
    )


def news_release(text: str, ctx: FixupContext) -> str:
    return _edit_first_match(
        text,
        _NEWS_RE,
        lambda m, post: (
            f"  Major changes between OpenSSL {m[1]} and OpenSSL"
            f" {ctx.release_text} [{ctx.release_date}]{post}"
        ),
    )


def news_md_release(text: str, ctx: FixupContext) -> str:
    # Unlike the other release fixups, a pre-release gets a placeholder date
    # rather than the real one.
    when = "in pre-release" if ctx.is_pre_release else ctx.release_date
    return _edit_first_match(
        text,
        _NEWS_MD_RE,
        lambda m, post: (
            f"### Major changes between OpenSSL {m[1]} and OpenSSL"
            f" {ctx.release_text} [{when}]{post}"
        ),
    )


def readme_release(text: str, ctx: FixupContext) -> str:
    return _edit_first_match(
        text,
        _README_RE,
        lambda m, post: f" OpenSSL {ctx.release} {ctx.release_date}{post}",
    )


def spec_version(text: str, ctx: FixupContext) -> str:
    """Update the Version: field of openssl.spec.

    The release and post-release variants of this fixup were byte-identical,
    so there is one function for both.
    """
    if "-pre" in ctx.release:
        return text
    release = re.sub(r"-dev$", "", ctx.release)
    return _edit_first_match(text, _SPEC_RE, lambda m, post: f"Version: {release}{post}")


# -- post-release fixups ----------------------------------------------------


def changes_postrelease(text: str, ctx: FixupContext) -> str:
    previous_date = ctx.prev_release_date or "xx XXX xxxx"

    def build(m: re.Match[str], post: str) -> str:
        v1 = m[1]
        v2 = ctx.prev_release_text or m[2]
        return (
            f" Changes between {v2} and {ctx.release_text} [xx XXX xxxx]\n"
            f"\n"
            f" *)\n"
            f"\n"
            f" Changes between {v1} and {v2} [{previous_date}]\n"
        )

    return _edit_first_match(text, _CHANGES_RE, build)


def changes_md_postrelease(text: str, ctx: FixupContext) -> str:
    previous_date = ctx.prev_release_date or "xx XXX xxxx"

    def build(m: re.Match[str], post: str) -> str | None:
        # A pre-release does not open a new changelog section.
        if ctx.is_pre_release:
            return None
        v1 = m[1]
        v2 = ctx.prev_release_text or m[2]
        return (
            f"### Changes between {v2} and {ctx.release_text} [xx XXX xxxx]\n"
            f"\n"
            f" * none yet\n"
            f"\n"
            f"### Changes between {v1} and {v2} [{previous_date}]\n"
        )

    return _edit_first_match(text, _CHANGES_MD_RE, build)


def news_postrelease(text: str, ctx: FixupContext) -> str:
    previous_date = ctx.prev_release_date or "under development"

    def build(m: re.Match[str], post: str) -> str:
        v1 = m[1]
        v2 = ctx.prev_release_text or m[2]
        return (
            f"  Major changes between OpenSSL {v2} and OpenSSL"
            f" {ctx.release_text} [under development]\n"
            f"\n"
            f"      o\n"
            f"\n"
            f"  Major changes between OpenSSL {v1} and OpenSSL"
            f" {v2} [{previous_date}]\n"
        )

    return _edit_first_match(text, _NEWS_RE, build)


def news_md_postrelease(text: str, ctx: FixupContext) -> str:
    previous_date = ctx.prev_release_date or "under development"

    def build(m: re.Match[str], post: str) -> str | None:
        if ctx.is_pre_release:
            return None
        v1 = m[1]
        v2 = ctx.prev_release_text or m[2]
        return (
            f"### Major changes between OpenSSL {v2} and OpenSSL"
            f" {ctx.release_text} [under development]\n"
            f"\n"
            f"  * none\n"
            f"\n"
            f"### Major changes between OpenSSL {v1} and OpenSSL"
            f" {v2} [{previous_date}]\n"
        )

    return _edit_first_match(text, _NEWS_MD_RE, build)


def readme_postrelease(text: str, ctx: FixupContext) -> str:
    return _edit_first_match(text, _README_RE, lambda m, post: f" OpenSSL {ctx.release}{post}")


#: (filename, direction) -> the edit to apply.
FIXUPS: dict[tuple[str, str], Fixup] = {
    ("CHANGES", RELEASE): changes_release,
    ("CHANGES", POSTRELEASE): changes_postrelease,
    ("CHANGES.md", RELEASE): changes_md_release,
    ("CHANGES.md", POSTRELEASE): changes_md_postrelease,
    ("NEWS", RELEASE): news_release,
    ("NEWS", POSTRELEASE): news_postrelease,
    ("NEWS.md", RELEASE): news_md_release,
    ("NEWS.md", POSTRELEASE): news_md_postrelease,
    ("README", RELEASE): readme_release,
    ("README", POSTRELEASE): readme_postrelease,
    ("openssl.spec", RELEASE): spec_version,
    ("openssl.spec", POSTRELEASE): spec_version,
}


def get_fixup(filename: str, direction: str) -> Fixup:
    """Look up the edit for `filename`, or raise KeyError if there is none."""
    return FIXUPS[(filename, direction)]

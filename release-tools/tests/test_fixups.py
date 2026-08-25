# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The per-file release and post-release edits.

These replace twelve `perl -pi` scripts.  Because a mistake here silently
corrupts a published changelog, each is checked against the exact text the
Perl produced.
"""
from __future__ import annotations

import pytest

from stagerelease.fixups import (
    FIXUPS,
    POSTRELEASE,
    RELEASE,
    FixupContext,
    changes_md_postrelease,
    changes_md_release,
    changes_postrelease,
    changes_release,
    news_md_postrelease,
    news_md_release,
    news_postrelease,
    news_release,
    readme_postrelease,
    readme_release,
    spec_version,
)

CHANGES_MD = (
    "### Changes between 3.1 and 3.2 [xx XXX xxxx]\n"
    "\n"
    " * Something.\n"
    "\n"
    "### Changes between 3.0 and 3.1 [xx XXX xxxx]\n"
)

NEWS_MD = (
    "### Major changes between OpenSSL 3.1 and OpenSSL 3.2 [under development]\n"
    "\n"
    "  * Something.\n"
)

CHANGES = " Changes between 1.0.2zg and 1.0.2zh [xx XXX xxxx]\n\n *)\n"

NEWS = (
    "  Major changes between OpenSSL 1.0.2zg and OpenSSL 1.0.2zh"
    " [under development]\n"
    "\n"
    "      o\n"
)


# -- release fixups ---------------------------------------------------------


def test_changes_md_release_stamps_version_and_date():
    ctx = FixupContext(release="3.2.0", release_text="3.2.0", release_date="25 Aug 2026")

    result = changes_md_release(CHANGES_MD, ctx)

    assert result.startswith("### Changes between 3.1 and 3.2.0 [25 Aug 2026]\n")


def test_changes_md_release_only_touches_the_first_heading():
    ctx = FixupContext(release="3.2.0", release_text="3.2.0", release_date="25 Aug 2026")

    result = changes_md_release(CHANGES_MD, ctx)

    assert "### Changes between 3.0 and 3.1 [xx XXX xxxx]\n" in result


def test_changes_release_uses_the_pre_3_0_heading():
    ctx = FixupContext(release_text="1.0.2zh", release_date="25 Aug 2026")

    result = changes_release(CHANGES, ctx)

    assert result == " Changes between 1.0.2zg and 1.0.2zh [25 Aug 2026]\n\n *)\n"


def test_news_md_release_stamps_the_date():
    ctx = FixupContext(release="3.2.0", release_text="3.2.0", release_date="25 Aug 2026")

    result = news_md_release(NEWS_MD, ctx)

    assert result.startswith(
        "### Major changes between OpenSSL 3.1 and OpenSSL 3.2.0 [25 Aug 2026]\n"
    )


def test_news_md_release_marks_a_pre_release_instead_of_dating_it():
    ctx = FixupContext(
        release="3.2.0-alpha1", release_text="3.2 alpha 1", release_date="25 Aug 2026"
    )

    result = news_md_release(NEWS_MD, ctx)

    assert "[in pre-release]" in result
    assert "25 Aug 2026" not in result


def test_news_release_uses_the_pre_3_0_heading():
    ctx = FixupContext(release_text="1.0.2zh", release_date="25 Aug 2026")

    result = news_release(NEWS, ctx)

    assert result.startswith(
        "  Major changes between OpenSSL 1.0.2zg and OpenSSL 1.0.2zh"
        " [25 Aug 2026]\n"
    )


def test_readme_release_rewrites_the_title_line():
    ctx = FixupContext(release="1.0.2zh", release_date="25 Aug 2026")

    result = readme_release(" OpenSSL 1.0.2zh-dev\n\n Body.\n", ctx)

    assert result == " OpenSSL 1.0.2zh 25 Aug 2026\n\n Body.\n"


def test_readme_postrelease_drops_the_date():
    ctx = FixupContext(release="1.0.2zi-dev")

    result = readme_postrelease(" OpenSSL 1.0.2zh 25 Aug 2026\n\n Body.\n", ctx)

    assert result == " OpenSSL 1.0.2zi-dev\n\n Body.\n"


def test_spec_version_is_updated():
    result = spec_version("Version:  1.0.2zg\nRelease: 1\n", FixupContext(release="1.0.2zh"))

    assert result == "Version: 1.0.2zh\nRelease: 1\n"


def test_spec_version_strips_a_dev_marker():
    result = spec_version("Version:  1.0.2zg\n", FixupContext(release="1.0.2zh-dev"))

    assert result == "Version: 1.0.2zh\n"


def test_spec_version_leaves_a_pre_release_alone():
    original = "Version:  1.0.2zg\n"

    assert spec_version(original, FixupContext(release="1.0.2zh-pre3")) == original


# -- post-release fixups ----------------------------------------------------


def test_changes_md_postrelease_opens_a_new_section():
    ctx = FixupContext(
        release="3.2.1-dev",
        release_text="3.2.1",
        prev_release_text="3.2.0",
        prev_release_date="25 Aug 2026",
    )

    result = changes_md_postrelease(CHANGES_MD, ctx)

    assert result.startswith(
        "### Changes between 3.2.0 and 3.2.1 [xx XXX xxxx]\n"
        "\n"
        " * none yet\n"
        "\n"
        "### Changes between 3.1 and 3.2.0 [25 Aug 2026]\n"
    )


def test_changes_md_postrelease_does_nothing_for_a_pre_release():
    # An alpha or beta does not open a new changelog section.
    ctx = FixupContext(
        release="3.2.0-alpha2-dev",
        release_text="3.2 alpha 2",
        prev_release_text="3.2 alpha 1",
    )

    assert changes_md_postrelease(CHANGES_MD, ctx) == CHANGES_MD


def test_news_md_postrelease_does_nothing_for_a_pre_release():
    ctx = FixupContext(release="3.2.0-beta1-dev", release_text="3.2 beta 1")

    assert news_md_postrelease(NEWS_MD, ctx) == NEWS_MD


def test_news_md_postrelease_opens_a_new_section():
    ctx = FixupContext(
        release="3.2.1-dev",
        release_text="3.2.1",
        prev_release_text="3.2.0",
        prev_release_date="25 Aug 2026",
    )

    result = news_md_postrelease(NEWS_MD, ctx)

    assert result.startswith(
        "### Major changes between OpenSSL 3.2.0 and OpenSSL 3.2.1"
        " [under development]\n"
        "\n"
        "  * none\n"
        "\n"
        "### Major changes between OpenSSL 3.1 and OpenSSL 3.2.0 [25 Aug 2026]\n"
    )


def test_changes_postrelease_uses_the_pre_3_0_placeholder():
    ctx = FixupContext(
        release_text="1.0.2zi", prev_release_text="1.0.2zh", prev_release_date="25 Aug 2026"
    )

    result = changes_postrelease(CHANGES, ctx)

    assert result == (
        " Changes between 1.0.2zh and 1.0.2zi [xx XXX xxxx]\n"
        "\n"
        " *)\n"
        "\n"
        " Changes between 1.0.2zg and 1.0.2zh [25 Aug 2026]\n"
        "\n"
        " *)\n"
    )


def test_news_postrelease_uses_the_pre_3_0_placeholder():
    ctx = FixupContext(release_text="1.0.2zi", prev_release_text="1.0.2zh")

    result = news_postrelease(NEWS, ctx)

    assert result.startswith(
        "  Major changes between OpenSSL 1.0.2zh and OpenSSL 1.0.2zi"
        " [under development]\n"
        "\n"
        "      o\n"
        "\n"
        "  Major changes between OpenSSL 1.0.2zg and OpenSSL 1.0.2zh"
        " [under development]\n"
    )


def test_postrelease_falls_back_to_the_heading_when_no_previous_release_given():
    # The minor-version bump on the update branch passes no PREV_RELEASE_TEXT,
    # so the second version in the heading is reused.
    ctx = FixupContext(release="3.3.0-dev", release_text="3.3")

    result = changes_md_postrelease(CHANGES_MD, ctx)

    assert result.startswith("### Changes between 3.2 and 3.3 [xx XXX xxxx]\n")
    assert "### Changes between 3.1 and 3.2 [xx XXX xxxx]\n" in result


# -- general behaviour ------------------------------------------------------


def test_a_file_with_no_matching_heading_is_untouched():
    original = "Nothing here matches.\n"

    for fixup in (changes_md_release, news_md_release, changes_md_postrelease):
        assert fixup(original, FixupContext(release="3.2.0")) == original


def test_form_feeds_survive():
    # str.splitlines() would treat \x0c as a line break and rewrite it.
    original = "\x0c\n### Changes between 3.1 and 3.2 [xx XXX xxxx]\n"

    result = changes_md_release(original, FixupContext(release_text="3.2.0"))

    assert result.startswith("\x0c\n")


def test_a_file_without_a_trailing_newline_is_not_given_one():
    original = "### Changes between 3.1 and 3.2 [xx XXX xxxx]"

    result = changes_md_release(original, FixupContext(release_text="3.2.0", release_date="x"))

    assert not result.endswith("\n")


@pytest.mark.parametrize("name", ["CHANGES", "CHANGES.md", "NEWS", "NEWS.md", "README"])
def test_every_release_file_has_both_directions(name):
    assert (name, RELEASE) in FIXUPS
    assert (name, POSTRELEASE) in FIXUPS


def test_is_pre_release_ignores_a_dev_marker():
    assert FixupContext(release="3.2.0-alpha1-dev").is_pre_release
    assert FixupContext(release="3.2.0-beta1").is_pre_release
    assert not FixupContext(release="3.2.1-dev").is_pre_release
    assert not FixupContext(release="3.2.1").is_pre_release

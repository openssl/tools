# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The OpenSSL 3.0+ versioning scheme."""
from __future__ import annotations

import pytest

from openssl_tools.stagerelease.errors import ReleaseError
from openssl_tools.stagerelease.version.modern import ModernScheme, parse_assignments

from tests.stagerelease.helpers import MODERN_VERSION_DAT


@pytest.fixture
def scheme() -> ModernScheme:
    return ModernScheme()


def test_parses_the_reference_version_file(scheme):
    state = scheme.parse(MODERN_VERSION_DAT)

    assert (state.major, state.minor, state.patch) == (3, 2, 0)
    assert state.dev is True
    assert state.pre_label == ""
    assert state.pre_release_tag == "dev"
    assert state.shlib_version == "3"
    assert state.release_date == ""


def test_derives_the_documented_values(scheme):
    state = scheme.parse(MODERN_VERSION_DAT)

    assert scheme.series(state) == "3.2"
    assert scheme.version(state) == "3.2.0"
    assert scheme.full_version(state) == "3.2.0-dev"
    assert scheme.release_files == ("CHANGES.md", "NEWS.md")


@pytest.mark.parametrize(
    "tag,dev,label,num",
    [
        ("", False, "", None),
        ("dev", True, "", 0),
        ("alpha1", False, "alpha", 1),
        ("alpha12-dev", True, "alpha", 12),
        ("beta3", False, "beta", 3),
        ("beta3-dev", True, "beta", 3),
    ],
)
def test_pre_release_tags_round_trip(scheme, tag, dev, label, num):
    state = scheme.parse(MODERN_VERSION_DAT.replace("PRE_RELEASE_TAG=dev", f"PRE_RELEASE_TAG={tag}"))

    assert (state.dev, state.pre_label, state.pre_num) == (dev, label, num)
    assert state.pre_release_tag == tag


def test_rejects_an_unrecognised_pre_release_tag(scheme):
    with pytest.raises(ReleaseError, match="Unrecognised PRE_RELEASE_TAG"):
        scheme.parse(MODERN_VERSION_DAT.replace("dev", "rc1"))


def test_rejects_a_version_file_missing_fields(scheme):
    with pytest.raises(ReleaseError, match="missing MAJOR"):
        scheme.parse("MINOR=2\nPATCH=0\n")


def test_rejects_a_non_numeric_version(scheme):
    with pytest.raises(ReleaseError, match="non-numeric"):
        scheme.parse("MAJOR=three\nMINOR=2\nPATCH=0\n")


def test_build_metadata_shows_up_in_the_full_version(scheme):
    state = scheme.parse(MODERN_VERSION_DAT.replace("BUILD_METADATA=", "BUILD_METADATA=quic"))

    assert state.marked_build_metadata == "+quic"
    assert scheme.full_version(state) == "3.2.0-dev+quic"


def test_renders_the_file_the_shell_produced(scheme):
    # The exact bytes release-aux/test_suite.sh asserted on, after the
    # sequence of transitions it ran.
    state = scheme.parse(MODERN_VERSION_DAT)
    state = scheme.bump(state, "minor")

    assert scheme.render(state, "") == (
        "MAJOR=3\n"
        "MINOR=3\n"
        "PATCH=0\n"
        "PRE_RELEASE_TAG=dev\n"
        "BUILD_METADATA=\n"
        'RELEASE_DATE=""\n'
        "SHLIB_VERSION=3\n"
    )


def test_render_parse_round_trip(scheme):
    state = scheme.parse(MODERN_VERSION_DAT)

    assert scheme.parse(scheme.render(state, "")) == state


def test_branch_and_tag_names(scheme):
    state = scheme.parse(MODERN_VERSION_DAT.replace("PRE_RELEASE_TAG=dev", "PRE_RELEASE_TAG=alpha1"))

    assert scheme.branch_name(state) == "openssl-3.2"
    assert scheme.tag_name(state) == "openssl-3.2.0-alpha1"


def test_next_patch_and_next_minor(scheme):
    state = scheme.parse(MODERN_VERSION_DAT)

    assert scheme.next_patch(0) == 1
    bumped = scheme.next_minor(state)
    assert (bumped.minor, bumped.patch) == (3, 0)


def test_parse_assignments_ignores_comments_and_blanks():
    values = parse_assignments("# a comment\n\nMAJOR=3\nRELEASE_DATE='1 Jan 2026'\n")

    assert values == {"MAJOR": "3", "RELEASE_DATE": "1 Jan 2026"}


def test_parse_assignments_does_not_execute_shell():
    # The shell ran VERSION.dat through eval; a plain parser cannot.
    values = parse_assignments("MAJOR=3\nPATCH=$(rm -rf /)\n")

    assert values["PATCH"] == "$(rm -rf /)"

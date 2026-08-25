# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The release state machine.

The first test walks exactly the sequence release-aux/test_suite.sh walked,
asserting the same values, so the port is pinned to the shell's behaviour.
The rest cover the transitions and rejections that suite never reached.
"""
from __future__ import annotations

from datetime import date

import pytest

from openssl_tools.stagerelease.errors import ReleaseError
from openssl_tools.stagerelease.state import format_release_date, next_release_state
from openssl_tools.stagerelease.version.legacy import LegacyScheme
from openssl_tools.stagerelease.version.modern import ModernScheme

from tests.stagerelease.helpers import LEGACY_OPENSSLV_H, MODERN_VERSION_DAT, TODAY, TODAY_TEXT


@pytest.fixture
def modern():
    return ModernScheme()


@pytest.fixture
def legacy():
    return LegacyScheme("crypto/opensslv.h", has_spec=True)


def describe(scheme, state):
    """The fields release-aux/test_suite.sh compared on."""
    return {
        "TYPE": state.type,
        "VERSION": scheme.version(state),
        "FULL_VERSION": scheme.full_version(state),
        "PRE_RELEASE_TAG": state.pre_release_tag,
        "RELEASE_DATE": state.release_date,
    }


def test_modern_release_cycle_matches_the_shell_test_suite(modern):
    state = modern.parse(MODERN_VERSION_DAT)

    assert describe(modern, state) == {
        "TYPE": "dev",
        "VERSION": "3.2.0",
        "FULL_VERSION": "3.2.0-dev",
        "PRE_RELEASE_TAG": "dev",
        "RELEASE_DATE": "",
    }

    steps = [
        ("alpha", "", "3.2.0", "3.2.0-alpha1", "alpha1", TODAY_TEXT),
        ("alpha", "dev", "3.2.0", "3.2.0-alpha2-dev", "alpha2-dev", ""),
        ("beta", "", "3.2.0", "3.2.0-beta1", "beta1", TODAY_TEXT),
        ("beta", "dev", "3.2.0", "3.2.0-beta2-dev", "beta2-dev", ""),
        ("final", "", "3.2.0", "3.2.0", "", TODAY_TEXT),
        ("final", "dev", "3.2.1", "3.2.1-dev", "dev", ""),
        ("", "", "3.2.1", "3.2.1", "", TODAY_TEXT),
        ("", "dev", "3.2.2", "3.2.2-dev", "dev", ""),
        ("minor", "dev", "3.3.0", "3.3.0-dev", "dev", ""),
    ]

    for method, type_, version, full, tag, when in steps:
        state = next_release_state(modern, state, method, TODAY)
        assert describe(modern, state) == {
            "TYPE": type_,
            "VERSION": version,
            "FULL_VERSION": full,
            "PRE_RELEASE_TAG": tag,
            "RELEASE_DATE": when,
        }, f"after next_release_state({method!r})"


def test_legacy_release_cycle_matches_the_shell_test_suite(legacy):
    state = legacy.parse(LEGACY_OPENSSLV_H)

    assert describe(legacy, state) == {
        "TYPE": "dev",
        "VERSION": "1.0.2zh",
        "FULL_VERSION": "1.0.2zh-dev",
        "PRE_RELEASE_TAG": "dev",
        "RELEASE_DATE": "",
    }

    state = next_release_state(legacy, state, "", TODAY)
    assert describe(legacy, state) == {
        "TYPE": "",
        "VERSION": "1.0.2zh",
        "FULL_VERSION": "1.0.2zh",
        "PRE_RELEASE_TAG": "",
        "RELEASE_DATE": TODAY_TEXT,
    }

    state = next_release_state(legacy, state, "", TODAY)
    assert describe(legacy, state) == {
        "TYPE": "dev",
        "VERSION": "1.0.2zi",
        "FULL_VERSION": "1.0.2zi-dev",
        "PRE_RELEASE_TAG": "dev",
        "RELEASE_DATE": "",
    }


def state_with(scheme, tag, patch=0):
    return scheme.parse(
        MODERN_VERSION_DAT.replace("PRE_RELEASE_TAG=dev", f"PRE_RELEASE_TAG={tag}")
        .replace("PATCH=0", f"PATCH={patch}")
    )


def test_next_beta_switches_an_alpha_series_over(modern):
    # --alpha --next-beta: release an alpha, then leave the branch in beta.
    state = state_with(modern, "alpha2-dev")

    released = next_release_state(modern, state, "alpha", TODAY)
    assert modern.full_version(released) == "3.2.0-alpha2"

    after = next_release_state(modern, released, "beta", TODAY)
    assert modern.full_version(after) == "3.2.0-beta1-dev"


def test_bare_next_continues_an_alpha_series(modern):
    # With no option given, an ongoing alpha series carries on as alpha.
    state = state_with(modern, "alpha2-dev")

    assert modern.full_version(next_release_state(modern, state, "", TODAY)) == (
        "3.2.0-alpha2"
    )


def test_bare_next_continues_a_beta_series(modern):
    state = state_with(modern, "beta4-dev")

    assert modern.full_version(next_release_state(modern, state, "", TODAY)) == (
        "3.2.0-beta4"
    )


@pytest.mark.parametrize(
    "tag,method,message",
    [
        ("beta1-dev", "alpha", "Invalid state for an alpha release"),
        ("", "alpha", "Invalid state for an alpha release"),
        ("", "beta", "Invalid state for beta release"),
        ("dev", "final", "Invalid state for final release"),
    ],
)
def test_impossible_transitions_are_rejected(modern, tag, method, message):
    with pytest.raises(ReleaseError, match=message):
        next_release_state(modern, state_with(modern, tag), method, TODAY)


def test_a_patch_release_from_zero_is_rejected(modern):
    # PATCH 0 means the series has never had a final release, so alpha or
    # beta has to come first.
    with pytest.raises(ReleaseError, match="Can't update PATCH version number from 0"):
        next_release_state(modern, state_with(modern, "dev", patch=0), "", TODAY)


def test_a_patch_release_from_nonzero_is_allowed(modern):
    state = state_with(modern, "dev", patch=7)

    assert modern.full_version(next_release_state(modern, state, "", TODAY)) == "3.2.7"


def test_legacy_patch_release_from_an_empty_patch_is_rejected(legacy):
    # 1.1.1 with no letter is the same situation as PATCH 0 above.
    state = legacy.parse(LEGACY_OPENSSLV_H.replace("0x10002210L", "0x10002000L"))
    assert state.patch == ""

    with pytest.raises(ReleaseError, match="Can't update PATCH"):
        next_release_state(legacy, state, "", TODAY)


def test_minor_is_allowed_from_any_phase(modern):
    for tag in ("dev", "alpha1-dev", "beta2-dev"):
        state = next_release_state(modern, state_with(modern, tag), "minor", TODAY)
        assert modern.full_version(state) == "3.3.0-dev"


def test_minor_steps_the_version_even_from_a_released_state(modern):
    # The transition moves the tree into development *before* bumping, so
    # the minor step is not gated on the tree already being in development.
    state = next_release_state(modern, state_with(modern, ""), "minor", TODAY)

    assert modern.full_version(state) == "3.3.0-dev"


def test_an_unknown_method_is_a_programming_error(modern):
    with pytest.raises(ValueError, match="unknown next method"):
        next_release_state(modern, state_with(modern, "dev"), "gamma", TODAY)


@pytest.mark.parametrize(
    "when,text",
    [
        (date(2026, 8, 25), "25 Aug 2026"),
        (date(2026, 1, 1), "1 Jan 2026"),
        (date(2026, 12, 9), "9 Dec 2026"),
    ],
)
def test_release_dates_have_no_leading_zero(when, text):
    # `date '+%-d %b %Y'` under LC_ALL=C.
    assert format_release_date(when) == text

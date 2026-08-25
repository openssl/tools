# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The pre-3.0 versioning scheme, including the patch letter chain."""
from __future__ import annotations

import pytest

from stagerelease.errors import ReleaseError
from stagerelease.version.legacy import LegacyScheme, decode_patch, encode_patch

from conftest import LEGACY_OPENSSLV_H


@pytest.fixture
def scheme() -> LegacyScheme:
    return LegacyScheme("crypto/opensslv.h", has_spec=True)


@pytest.mark.parametrize(
    "number,letters",
    [
        (0, ""),
        (1, "a"),
        (2, "b"),
        (25, "y"),
        (26, "za"),
        (33, "zh"),
        (34, "zi"),
        (50, "zy"),
        (51, "zza"),
        (75, "zzy"),
        (76, "zzza"),
    ],
)
def test_patch_encoding_matches_the_documented_scheme(number, letters):
    assert encode_patch(number) == letters
    assert decode_patch(letters) == number


@pytest.mark.parametrize("number", range(0, 120))
def test_patch_encoding_round_trips(number):
    # The shell's set_version() could not do this: its `^(z)*(.)$` captured
    # only the last 'z', so any chain longer than one 'z' decoded wrongly.
    assert decode_patch(encode_patch(number)) == number


def test_patch_encoding_rejects_nonsense():
    with pytest.raises(ReleaseError):
        decode_patch("qq")
    with pytest.raises(ReleaseError):
        encode_patch(-1)


def test_parses_the_reference_header(scheme):
    state = scheme.parse(LEGACY_OPENSSLV_H)

    assert (state.major, state.minor, state.fix) == (1, 0, 2)
    assert state.patch == "zh"
    assert state.dev is True
    assert state.shlib_version == "1.0.0"


def test_derives_the_documented_values(scheme):
    state = scheme.parse(LEGACY_OPENSSLV_H)

    assert scheme.series(state) == "1.0.2"
    assert scheme.version(state) == "1.0.2zh"
    assert scheme.full_version(state) == "1.0.2zh-dev"
    assert scheme.release_files == ("README", "CHANGES", "NEWS", "openssl.spec")


def test_release_files_omit_the_spec_when_it_is_not_tracked():
    scheme = LegacyScheme("include/openssl/opensslv.h", has_spec=False)

    assert scheme.release_files == ("README", "CHANGES", "NEWS")


def test_shlib_version_for_a_1_1_branch():
    scheme = LegacyScheme("include/openssl/opensslv.h", has_spec=False)
    header = LEGACY_OPENSSLV_H.replace("0x10002210L", "0x1010115fL")

    assert scheme.parse(header).shlib_version == "1.1"


def test_release_state_is_recognised(scheme):
    # The final hex digit is the state: 0 for development, f for released.
    state = scheme.parse(LEGACY_OPENSSLV_H.replace("0x10002210L", "0x1000221fL"))

    assert state.dev is False
    assert scheme.full_version(state) == "1.0.2zh"


def test_rejects_a_header_without_a_version(scheme):
    with pytest.raises(ReleaseError, match="No OPENSSL_VERSION_NUMBER"):
        scheme.parse("/* nothing to see here */\n")


def test_renders_the_header_the_shell_produced(scheme):
    # The exact bytes release-aux/test_suite.sh asserted on after a
    # post-release step from 1.0.2zh.
    state = scheme.parse(LEGACY_OPENSSLV_H)
    state = scheme.bump(state, "")

    assert scheme.render(state, LEGACY_OPENSSLV_H) == (
        "# define OPENSSL_VERSION_NUMBER  0x10002220L\n"
        "# ifdef OPENSSL_FIPS\n"
        '#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zi-fips-dev'
        '  xx XXX xxxx"\n'
        "# else\n"
        '#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zi-dev  xx XXX xxxx"\n'
        "# endif\n"
        '# define OPENSSL_VERSION_PTEXT   " part of " OPENSSL_VERSION_TEXT\n'
    )


def test_render_updates_every_version_text_line(scheme):
    # Both the fips and non-fips definitions must move; `perl -pi` rewrote
    # each matching line, not just the first.
    state = scheme.parse(LEGACY_OPENSSLV_H)
    rendered = scheme.render(scheme.bump(state, ""), LEGACY_OPENSSLV_H)

    assert rendered.count("1.0.2zi") == 2
    assert "1.0.2zh" not in rendered


def test_render_stamps_the_release_date(scheme):
    from dataclasses import replace

    state = scheme.parse(LEGACY_OPENSSLV_H)
    released = replace(state, dev=False, release_date="25 Aug 2026")
    rendered = scheme.render(released, LEGACY_OPENSSLV_H)

    assert '"OpenSSL 1.0.2zh  25 Aug 2026"' in rendered
    # State digit f marks a release.
    assert "0x1000221fL" in rendered


def test_render_updates_the_shlib_version(scheme):
    header = LEGACY_OPENSSLV_H + '# define SHLIB_VERSION_NUMBER "0.9.8"\n'
    state = scheme.parse(LEGACY_OPENSSLV_H)

    assert '# define SHLIB_VERSION_NUMBER "1.0.0"\n' in scheme.render(state, header)


def test_render_leaves_unrelated_lines_alone(scheme):
    state = scheme.parse(LEGACY_OPENSSLV_H)
    rendered = scheme.render(state, LEGACY_OPENSSLV_H)

    assert '# define OPENSSL_VERSION_PTEXT   " part of " OPENSSL_VERSION_TEXT' in rendered


def test_branch_and_tag_names(scheme):
    state = scheme.parse(LEGACY_OPENSSLV_H)

    assert scheme.branch_name(state) == "OpenSSL_1_0_2-stable"
    assert scheme.tag_name(state) == "OpenSSL_1_0_2zh"


def test_next_minor_steps_fix_and_clears_the_patch(scheme):
    state = scheme.parse(LEGACY_OPENSSLV_H)
    bumped = scheme.next_minor(state)

    assert (bumped.fix, bumped.patch) == (3, "")
    assert scheme.version(bumped) == "1.0.3"


# The two cases below are where a differential run against the shell
# functions disagreed.  In both the shell wrote a corrupt
# OPENSSL_VERSION_NUMBER, because its decoder was `^(z)*(.)$` -- a capture
# group under `*`, which keeps only the last repetition.  Neither was
# reachable in practice (1.x is end-of-life and never went past 'zh'), but
# the values below are the correct ones.


def test_an_empty_patch_encodes_as_zero(scheme):
    # The shell produced 0x10003ffffffffffffffa00L here: its regex failed to
    # match an empty patch, so it computed ord(undef) - ord('a') + 1 = -96.
    state = scheme.parse(LEGACY_OPENSSLV_H)
    rendered = scheme.render(scheme.next_minor(state), LEGACY_OPENSSLV_H)

    assert "0x10003000L" in rendered


def test_a_two_z_patch_chain_encodes_correctly(scheme):
    # 1.0.2zy is PP=50, so 1.0.2zza is PP=51 -> 0x33.  The shell wrote 0x1a
    # (26), having read 'zza' as a single-'z' chain.
    zy = LEGACY_OPENSSLV_H.replace("0x10002210L", "0x10002320L")
    state = scheme.parse(zy)
    assert state.patch == "zy"

    stepped = scheme.bump(state, "")
    assert stepped.patch == "zza"
    assert "0x10002330L" in scheme.render(stepped, zy)

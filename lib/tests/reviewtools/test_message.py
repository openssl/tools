# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Commit message trailer rewriting.

These run against the real `git interpret-trailers`, because that is what
places the trailer block and what the assertions are really about.  It costs
a few milliseconds per call.
"""

from __future__ import annotations

import pytest

from openssl_tools.reviewtools.message import (
    format_merge_date,
    interpret_trailers,
    is_trivial,
    merged_from_url,
    rewrite,
    split_lines,
)
from tests.reviewtools.helpers import FROZEN_MERGE_DATE, FROZEN_TIME, LEVITTE, STEVE

BODY = "Fix a thing\n\nThe thing was broken.\n"


def rewritten(message=BODY, **kwargs):
    kwargs.setdefault("reviewers", [STEVE])
    kwargs.setdefault("repo", "openssl")
    kwargs.setdefault("now", FROZEN_TIME)
    return rewrite(message, **kwargs)


# -- the basics -------------------------------------------------------------


def test_a_reviewer_and_a_merge_date_are_added():
    assert rewritten() == (
        "Fix a thing\n"
        "\n"
        "The thing was broken.\n"
        "\n"
        f"Reviewed-by: {STEVE}\n"
        f"Merge-date: {FROZEN_MERGE_DATE}\n"
    )


def test_several_reviewers_keep_their_order():
    result = rewritten(reviewers=[LEVITTE, STEVE])

    assert result.index(f"Reviewed-by: {LEVITTE}") < result.index(f"Reviewed-by: {STEVE}")


def test_a_pr_number_becomes_a_merged_from_trailer():
    result = rewritten(prnum="12345")

    assert result.endswith("Merged-from: https://github.com/openssl/openssl/pull/12345\n")


def test_the_merged_from_trailer_names_the_right_repository():
    assert "https://github.com/openssl/tools/pull/7\n" in rewritten(repo="tools", prnum="7")


def test_a_release_line_is_added():
    assert "Release: yes\n" in rewritten(release=True)


# -- existing trailers ------------------------------------------------------


def test_an_already_credited_reviewer_is_not_repeated():
    # Delegated to addIfDifferent rather than filtered here.
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    result = rewritten(message, reviewers=[STEVE, LEVITTE])

    assert result.count(f"Reviewed-by: {STEVE}") == 1
    assert f"Reviewed-by: {LEVITTE}" in result


def test_existing_reviewers_stay_in_the_trailer_block():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    assert rewritten(message, reviewers=[LEVITTE]) == (
        "Fix a thing\n"
        "\n"
        f"Reviewed-by: {STEVE}\n"
        f"Reviewed-by: {LEVITTE}\n"
        f"Merge-date: {FROZEN_MERGE_DATE}\n"
    )


def test_an_existing_merge_date_is_kept_and_not_duplicated():
    message = "Fix a thing\n\nMerge-date: Mon Jan  1 00:00:00 2020\n"

    result = rewritten(message)

    assert result.count("Merge-date:") == 1
    assert "Mon Jan  1 00:00:00 2020" in result


def test_the_old_mergedate_spelling_is_recognised():
    # Messages written before the trailer became compliant.
    message = "Fix a thing\n\nMergeDate: Mon Jan  1 00:00:00 2020\n"

    result = rewritten(message)

    assert FROZEN_MERGE_DATE not in result


def test_an_existing_release_line_is_moved_into_the_trailer_block():
    message = "Fix a thing\n\nRelease: yes\n\nMore body.\n"

    result = rewritten(message, release=True)

    assert result.count("Release: yes") == 1
    assert result.rstrip("\n").endswith("Release: yes")


def test_a_release_line_is_left_alone_when_not_a_release_run():
    assert "Release: yes" in rewritten("Fix a thing\n\nRelease: yes\n", release=False)


def test_an_old_prose_merge_reference_is_replaced():
    message = "Fix a thing\n\n(Merged from https://github.com/openssl/openssl/pull/1)\n"

    result = rewritten(message, prnum="2")

    assert "Merged from" not in result
    assert result.endswith("Merged-from: https://github.com/openssl/openssl/pull/2\n")


def test_an_existing_merged_from_trailer_is_replaced():
    message = "Fix a thing\n\nMerged-from: https://github.com/openssl/openssl/pull/1\n"

    result = rewritten(message, prnum="2")

    assert "pull/1" not in result
    assert "pull/2" in result


def test_a_merge_reference_is_dropped_when_no_number_is_given():
    # This is what --nopr does, and it is deliberate.
    message = "Fix a thing\n\nMerged-from: https://github.com/openssl/openssl/pull/1\n"

    assert "Merged-from" not in rewritten(message)


def test_a_merge_reference_for_another_repository_is_left_alone():
    message = "Fix a thing\n\n(Merged from https://github.com/openssl/tools/pull/1)\n"

    assert "openssl/tools/pull/1" in rewritten(message, repo="openssl")


# -- removal ----------------------------------------------------------------


def test_remove_reviewers_strips_existing_trailers():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\nReviewed-by: {LEVITTE}\n"

    result = rewritten(message, reviewers=[], remove_reviewers=True)

    assert "Reviewed-by:" not in result
    assert f"Merge-date: {FROZEN_MERGE_DATE}" in result


def test_remove_reviewers_adds_none():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    assert "Reviewed-by:" not in rewritten(message, remove_reviewers=True)


# -- edge cases -------------------------------------------------------------


def test_trailing_blank_lines_do_not_double_the_separator():
    assert rewritten("Fix a thing\n\n\n\n") == (
        f"Fix a thing\n\nReviewed-by: {STEVE}\nMerge-date: {FROZEN_MERGE_DATE}\n"
    )


def test_an_all_blank_message_does_not_hang():
    # The Perl looped forever here: popping an empty array left undef, which
    # matched its "blank line" test.
    assert f"Merge-date: {FROZEN_MERGE_DATE}" in rewritten("\n\n\n")


def test_a_message_without_a_trailing_newline_is_handled():
    assert rewritten("Fix a thing").startswith("Fix a thing\n")


def test_crlf_line_endings_are_normalised():
    assert "\r" not in rewritten("Fix a thing\r\n\r\nBody.\r\n")


def test_form_feeds_are_not_treated_as_line_breaks():
    assert "\x0c" in rewritten("Fix a thing\n\n\x0cBody.\n")


@pytest.mark.parametrize(
    "line,expected",
    [
        ("CLA: Trivial", True),
        ("cla: trivial", True),
        ("CLA:   Trivial  ", True),
        ("CLA: Trivial extra", False),
        ("Not a CLA: Trivial", False),
    ],
)
def test_trivial_marker_detection(line, expected):
    assert is_trivial(f"Subject\n\n{line}\n") is expected


def test_merge_date_matches_the_perl_format():
    # Perl's `scalar gmtime`: ctime layout, space-padded day.
    assert format_merge_date(FROZEN_TIME) == "Tue Aug 25 12:34:56 2026"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("a\nb\n", ["a", "b"]),
        ("a\nb", ["a", "b"]),
        ("", []),
        ("\n", [""]),
        ("a\r\nb\r\n", ["a", "b"]),
        ("a\n\x0cb\n", ["a", "\x0cb"]),
    ],
)
def test_split_lines(text, expected):
    assert [line.rstrip("\n") for line in split_lines(text)] == expected


def test_merged_from_url():
    assert merged_from_url("fuzz-corpora", "9") == (
        "https://github.com/openssl/fuzz-corpora/pull/9"
    )


# -- the delegation itself --------------------------------------------------


def test_interpret_trailers_adds_the_separating_blank_line():
    assert interpret_trailers("Subject only\n", ["Release: yes"]) == (
        "Subject only\n\nRelease: yes\n"
    )


def test_add_trailers_is_injectable():
    seen = {}

    def fake(body, trailers):
        seen["body"] = body
        seen["trailers"] = list(trailers)
        return "replaced\n"

    assert rewritten(add_trailers=fake) == "replaced\n"
    assert seen["body"] == "Fix a thing\n\nThe thing was broken.\n"
    assert seen["trailers"] == [
        f"Reviewed-by: {STEVE}",
        f"Merge-date: {FROZEN_MERGE_DATE}",
    ]

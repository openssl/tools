# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Commit message trailer rewriting."""
from __future__ import annotations

import pytest

from reviewtools.message import (
    format_merge_date,
    is_trivial,
    merged_from_prefix,
    rewrite,
    split_lines,
)

from conftest import FROZEN_MERGE_DATE, FROZEN_TIME, LEVITTE, STEVE

BODY = "Fix a thing\n\nThe thing was broken.\n"


def rewritten(message=BODY, **kwargs):
    kwargs.setdefault("reviewers", [STEVE])
    kwargs.setdefault("repo", "openssl")
    kwargs.setdefault("now", FROZEN_TIME)
    return rewrite(message, **kwargs)


# -- the basics -------------------------------------------------------------


def test_a_reviewer_is_appended_after_a_blank_line():
    assert rewritten() == (
        "Fix a thing\n"
        "\n"
        "The thing was broken.\n"
        "\n"
        f"Reviewed-by: {STEVE}\n"
        f"MergeDate: {FROZEN_MERGE_DATE}\n"
    )


def test_several_reviewers_keep_their_order():
    result = rewritten(reviewers=[LEVITTE, STEVE])

    assert result.index(f"Reviewed-by: {LEVITTE}") < result.index(
        f"Reviewed-by: {STEVE}"
    )


def test_a_pr_reference_is_added_last():
    result = rewritten(prnum="12345")

    assert result.endswith(
        "(Merged from https://github.com/openssl/openssl/pull/12345)\n"
    )


def test_the_pr_reference_names_the_right_repository():
    result = rewritten(repo="tools", prnum="7")

    assert "https://github.com/openssl/tools/pull/7)" in result


def test_a_release_line_is_added():
    result = rewritten(release=True)

    assert result.endswith(f"MergeDate: {FROZEN_MERGE_DATE}\nRelease: yes\n")


# -- existing trailers ------------------------------------------------------


def test_an_already_credited_reviewer_is_not_repeated():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    result = rewritten(message, reviewers=[STEVE, LEVITTE])

    assert result.count(f"Reviewed-by: {STEVE}") == 1
    assert f"Reviewed-by: {LEVITTE}" in result


def test_no_blank_line_is_inserted_into_a_run_of_trailers():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    result = rewritten(message, reviewers=[LEVITTE])

    assert result == (
        "Fix a thing\n"
        "\n"
        f"Reviewed-by: {STEVE}\n"
        f"Reviewed-by: {LEVITTE}\n"
        f"MergeDate: {FROZEN_MERGE_DATE}\n"
    )


def test_an_existing_merge_date_is_kept_and_not_duplicated():
    message = "Fix a thing\n\nMergeDate: Mon Jan  1 00:00:00 2020\n"

    result = rewritten(message)

    assert result.count("MergeDate:") == 1
    assert "Mon Jan  1 00:00:00 2020" in result


def test_an_existing_release_line_is_moved_to_the_end():
    message = "Fix a thing\n\nRelease: yes\n\nMore body.\n"

    result = rewritten(message, release=True)

    assert result.count("Release: yes") == 1
    assert result.endswith("Release: yes\n")


def test_a_release_line_is_left_alone_when_not_a_release_run():
    message = "Fix a thing\n\nRelease: yes\n"

    assert "Release: yes" in rewritten(message, release=False)


def test_an_old_pr_reference_is_replaced():
    message = (
        "Fix a thing\n\n"
        "(Merged from https://github.com/openssl/openssl/pull/1)\n"
    )

    result = rewritten(message, prnum="2")

    assert "pull/1)" not in result
    assert result.endswith("pull/2)\n")


def test_a_pr_reference_is_dropped_when_no_number_is_given():
    # This is what `--nopr` does, and it is deliberate.
    message = (
        "Fix a thing\n\n"
        "(Merged from https://github.com/openssl/openssl/pull/1)\n"
    )

    assert "Merged from" not in rewritten(message)


def test_a_pr_reference_for_another_repository_is_left_alone():
    message = (
        "Fix a thing\n\n"
        "(Merged from https://github.com/openssl/tools/pull/1)\n"
    )

    assert "openssl/tools/pull/1" in rewritten(message, repo="openssl")


# -- removal ----------------------------------------------------------------


def test_remove_reviewers_strips_existing_trailers():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\nReviewed-by: {LEVITTE}\n"

    result = rewritten(message, reviewers=[], remove_reviewers=True)

    assert "Reviewed-by:" not in result
    assert result == f"Fix a thing\n\nMergeDate: {FROZEN_MERGE_DATE}\n"


def test_remove_reviewers_adds_none():
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    assert "Reviewed-by:" not in rewritten(message, remove_reviewers=True)


# -- edge cases -------------------------------------------------------------


def test_trailing_blank_lines_are_dropped_before_trailers_are_added():
    result = rewritten("Fix a thing\n\n\n\n")

    assert result == (
        f"Fix a thing\n\nReviewed-by: {STEVE}\nMergeDate: {FROZEN_MERGE_DATE}\n"
    )


def test_an_all_blank_message_does_not_hang():
    # The Perl looped forever here: popping an empty array left undef, which
    # matched its "blank line" test.
    result = rewritten("\n\n\n")

    assert result.endswith(f"MergeDate: {FROZEN_MERGE_DATE}\n")


def test_a_message_without_a_trailing_newline_is_handled():
    assert rewritten("Fix a thing").startswith("Fix a thing\n")


def test_crlf_line_endings_are_normalised():
    assert "\r" not in rewritten("Fix a thing\r\n\r\nBody.\r\n")


def test_form_feeds_are_not_treated_as_line_breaks():
    result = rewritten("Fix a thing\n\n\x0cBody.\n")

    assert "\x0c" in result


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
    assert split_lines(text) == expected


def test_merged_from_prefix():
    assert merged_from_prefix("web") == (
        "(Merged from https://github.com/openssl/web/pull/"
    )

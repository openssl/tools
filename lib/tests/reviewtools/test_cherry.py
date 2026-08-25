# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""cherry-checker's parsing, sorting and formatting."""

from __future__ import annotations

import io

import pytest

from openssl_tools.reviewtools.cherry import (
    Commit,
    extract_fixes,
    extract_prnum,
    format_table,
    parse_log_line,
    pick_cherries,
    pick_default_right,
    shorten,
)
from openssl_tools.reviewtools.cherry_cli import main
from openssl_tools.reviewtools.errors import ReviewError

SEP = "\x1f"


class FakeGit:
    """Answers the handful of git questions cherry-checker asks."""

    def __init__(
        self,
        log=(),
        messages=None,
        branches=(),
        remote="upstream",
        remotes="origin\tgit@github.com:me/openssl.git (push)\n",
    ):
        self._log = list(log)
        self._messages = messages or {}
        self._branches = list(branches)
        self._remote = remote
        self._remotes = remotes

    def remotes(self):
        return self._remotes

    def branches(self):
        return self._branches

    def master_remote(self):
        return self._remote

    def symmetric_difference(self, left, right):
        return self._log

    def message(self, commit):
        return self._messages.get(commit, "")


# -- field extraction -------------------------------------------------------


def test_prnum_from_the_standard_merge_annotation():
    message = "(Merged from https://github.com/openssl/openssl/pull/12345)"

    assert extract_prnum(message) == "12345"


def test_prnum_from_the_older_gh_annotation():
    assert extract_prnum("GH: #987") == "987"


def test_prnum_is_unknown_when_absent():
    assert extract_prnum("Just a commit.") == "????"


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Fixes #42", "#42"),
        ("Fixes: #42", "#42"),
        ("Fixes https://github.com/openssl/openssl/pull/42", "#42"),
        ("Nothing here", ""),
    ],
)
def test_fixes_extraction(message, expected):
    assert extract_fixes(message) == expected


def test_long_subjects_are_shortened():
    assert shorten("x" * 80).endswith("...")
    assert len(shorten("x" * 80)) == 73


def test_short_subjects_are_untouched():
    assert shorten("brief") == "brief"


# -- log parsing ------------------------------------------------------------


def test_a_log_line_is_parsed():
    line = f"1700000000{SEP}<{SEP}abc1234{SEP}Fix a thing"

    assert parse_log_line(line) == (1700000000, "<", "abc1234", "Fix a thing")


def test_a_subject_containing_the_separator_character_is_impossible():
    # %s cannot contain \x1f, so the split is safe; a subject with other
    # punctuation must survive intact.
    line = f"1700000000{SEP}>{SEP}abc1234{SEP}Fix a; thing | with, punctuation"

    _, _, _, subject = parse_log_line(line)
    assert subject == "Fix a; thing | with, punctuation"


@pytest.mark.parametrize(
    "line",
    ["", "garbage", f"nottime{SEP}<{SEP}abc{SEP}s", f"170{SEP}?{SEP}abc{SEP}s"],
)
def test_unparseable_lines_are_skipped(line):
    assert parse_log_line(line) is None


# -- selection --------------------------------------------------------------


def test_already_picked_commits_are_skipped_by_default():
    git = FakeGit(
        log=[
            f"100{SEP}<{SEP}aaa{SEP}Only on the left",
            f"200{SEP}={SEP}bbb{SEP}On both sides",
        ]
    )

    commits = list(pick_cherries(git, "master", "openssl-3.5"))

    assert [entry.commit for entry in commits] == ["aaa"]


def test_all_includes_picked_commits():
    git = FakeGit(
        log=[
            f"100{SEP}<{SEP}aaa{SEP}Only on the left",
            f"200{SEP}={SEP}bbb{SEP}On both sides",
        ]
    )

    commits = list(pick_cherries(git, "master", "openssl-3.5", include_picked=True))

    assert [entry.commit for entry in commits] == ["aaa", "bbb"]


def test_pr_numbers_come_from_the_commit_message():
    git = FakeGit(
        log=[f"100{SEP}<{SEP}aaa{SEP}Fix"],
        messages={
            "aaa": "Fix\n\nFixes #7\n(Merged from https://github.com/openssl/openssl/pull/99)\n"
        },
    )

    (entry,) = pick_cherries(git, "master", "openssl-3.5")

    assert (entry.prnum, entry.fixes) == ("99", "#7")


# -- sorting ----------------------------------------------------------------


def test_pr_numbers_sort_numerically():
    # The previous implementation sorted the strings, putting #9999 above
    # #10000.
    low = Commit("9999", "", 1, "<", "aaa", "s")
    high = Commit("10000", "", 1, "<", "bbb", "s")

    assert sorted([low, high], key=lambda c: c.sort_key) == [low, high]


def test_commits_without_a_pr_number_sort_last():
    unknown = Commit("????", "", 5, "<", "aaa", "s")
    known = Commit("1", "", 1, "<", "bbb", "s")

    assert sorted([unknown, known], key=lambda c: c.sort_key) == [unknown, known]


# -- default branch selection ----------------------------------------------


@pytest.mark.parametrize(
    "branches,expected",
    [
        (["master", "openssl-3.2", "openssl-3.5"], "openssl-3.5"),
        (["openssl-3.10", "openssl-3.9"], "openssl-3.10"),
        (["master", "openssl-4.0", "openssl-3.5"], "openssl-4.0"),
        (["origin/openssl-3.5"], "origin/openssl-3.5"),
        (["master", "OpenSSL_1_1_1-stable"], None),
        ([], None),
    ],
)
def test_default_right_picks_the_highest_release_branch(branches, expected):
    # Hardcoding this was how the old default came to be an end-of-life
    # branch; 3.10 must also beat 3.9, which a string comparison would not.
    assert pick_default_right(branches) == expected


# -- formatting -------------------------------------------------------------


def test_the_table_has_a_row_per_commit():
    commits = [
        Commit("99", "#7", 1, "<", "aaa1234", "Fix a thing"),
        Commit("????", "", 2, "=", "bbb5678", "Another thing"),
    ]

    table = format_table(commits, "master", "openssl-3.5")

    assert "  <-  master" in table
    assert "  ->  openssl-3.5" in table
    assert "   #99 |     #7 | <- | aaa1234 | Fix a thing " in table
    assert " #???? |        | == | bbb5678 | Another thing " in table


# -- the command line -------------------------------------------------------


def run(argv, git):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, stdout=out, stderr=err, git=git)
    return code, out.getvalue(), err.getvalue()


def test_a_non_openssl_repository_is_refused():
    git = FakeGit(remotes="origin\tgit@example.invalid:me/other.git (push)\n")

    code, _, err = run([], git)

    assert code == 1
    assert "Not inside an openssl git repository" in err


def test_the_default_right_branch_is_discovered():
    git = FakeGit(branches=["master", "openssl-3.5"], log=[])

    code, out, _ = run([], git)

    assert code == 0
    assert "->  openssl-3.5" in out


def test_a_missing_release_branch_is_reported():
    git = FakeGit(branches=["master"])

    code, _, err = run([], git)

    assert code == 1
    assert "could not find a local openssl-N.M branch" in err


def test_explicit_branches_are_used():
    git = FakeGit(branches=["master"], log=[])

    code, out, _ = run(["openssl-3.4", "openssl-3.5"], git)

    assert code == 0
    assert "<-  openssl-3.4" in out
    assert "->  openssl-3.5" in out


def test_remote_prefixes_both_branches():
    # The old code called a non-existent .trim(), swallowed the
    # AttributeError, and always used "origin".
    git = FakeGit(branches=["master", "openssl-3.5"], log=[], remote="upstream")

    _, out, _ = run(["-r"], git)

    assert "<-  upstream/master" in out
    assert "->  upstream/openssl-3.5" in out


def test_running_outside_a_repository_reports_the_intended_message():
    class NoRepo(FakeGit):
        def remotes(self):
            raise ReviewError("git remote -v failed: not a git repository")

    code, _, err = run([], NoRepo())

    assert code == 1
    assert "Not inside an openssl git repository" in err
    assert "not a git repository" not in err

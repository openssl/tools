# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The addrev command line interface.

The execution tests run against real throwaway repositories: addrev rewrites
the range with git plumbing, and that is what is worth exercising.
"""

from __future__ import annotations

import io
import os

from openssl_tools.reviewtools import addrev_cli, listing
from tests.reviewtools.helpers import LEVITTE, STEVE, FakePeople, run_git


def make_repo(tmp_path, commits=2, author="contributor@example.invalid"):
    root = tmp_path / "repo"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main")
    # By default an outside contributor: has a CLA, is not a committer, and is
    # not one of the reviewers the tests name.
    run_git(root, "config", "user.email", author)
    run_git(root, "config", "user.name", "A Contributor")
    for n in range(commits):
        (root / f"f{n}").write_text("x\n")
        run_git(root, "add", "-A")
        run_git(root, "commit", "-q", "-m", f"Commit {n}\n\nBody {n}.\n")
    return root


def addrev(root, argv, people=None):
    out, err = io.StringIO(), io.StringIO()
    cwd = os.getcwd()
    os.chdir(root)
    try:
        code = addrev_cli.main(argv, stdout=out, stderr=err, query=people or FakePeople())
    finally:
        os.chdir(cwd)
    return code, out.getvalue(), err.getvalue()


def head_message(root, ref="HEAD"):
    return run_git(root, "log", "-1", "--pretty=%B", ref)


# -- reviewer rules, end to end ---------------------------------------------


def test_two_reviewers_are_added(tmp_path):
    root = make_repo(tmp_path)

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in head_message(root)
    assert f"Reviewed-by: {LEVITTE}" in head_message(root)


def test_one_reviewer_is_refused_for_the_main_repository(tmp_path):
    root = make_repo(tmp_path)

    code, _, err = addrev(root, ["--nopr", "--noself", "steve"])

    assert code == 1
    assert "Too few reviewers" in err
    assert "Reviewed-by:" not in head_message(root)


def test_the_author_counts_for_tools(tmp_path):
    root = make_repo(tmp_path, author="steve@openssl.org")

    code, _, err = addrev(root, ["--nopr", "--noself", "--tools", "levitte"])

    assert code == 0, err
    assert f"Reviewed-by: {LEVITTE}" in head_message(root)
    # An author never gets a trailer, even when they count.
    assert STEVE not in head_message(root)


def test_a_non_committer_reviewer_is_refused(tmp_path):
    root = make_repo(tmp_path)

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "outsider"])

    assert code == 1
    assert "not committers: outsider" in err
    assert "addrev --list" in err


def test_a_reviewer_who_wrote_one_of_the_commits_is_refused_by_name(tmp_path):
    # openssl/openssl PR 32357: three commits, one of them by a reviewer named
    # on the command line.  Only that commit is short of reviewers, and saying
    # which one is the whole diagnosis.
    root = make_repo(tmp_path, commits=2)
    (root / "own").write_text("x\n")
    run_git(root, "add", "-A")
    run_git(
        root,
        "-c",
        "user.email=steve@openssl.org",
        "-c",
        "user.name=Steve Henson",
        "commit",
        "-q",
        "-m",
        "Steve fixes his own thing\n",
    )
    before = run_git(root, "rev-parse", "HEAD")

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte", "-2"])

    assert code == 1
    assert "Steve fixes his own thing" in err
    assert "Too few reviewers" in err
    assert "authored this commit" in err
    # Nothing is written until the whole range validates.
    assert run_git(root, "rev-parse", "HEAD") == before


def test_a_non_trivial_commit_from_an_author_without_a_cla_is_refused(tmp_path):
    root = make_repo(tmp_path, author="nocla@example.invalid")

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 1
    assert "has no CLA" in err


def test_a_trivial_marker_in_the_message_allows_a_missing_cla(tmp_path):
    root = make_repo(tmp_path, author="nocla@example.invalid")
    run_git(root, "commit", "-q", "--amend", "-m", "Fix a thing\n\nCLA: Trivial\n")

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in head_message(root)


# -- trailers ---------------------------------------------------------------


def test_a_pr_number_adds_a_merged_from_trailer(tmp_path):
    root = make_repo(tmp_path)

    addrev(root, ["999", "--noself", "steve", "levitte"])

    assert (
        head_message(root)
        .rstrip("\n")
        .endswith("Merged-from: https://github.com/openssl/openssl/pull/999")
    )


def test_release_adds_a_release_line(tmp_path):
    root = make_repo(tmp_path)

    addrev(root, ["--nopr", "--noself", "--release", "steve", "levitte"])

    assert "Release: yes" in head_message(root)


def test_rmreviewers_strips_trailers_without_adding_any(tmp_path):
    # Quirk carried over from gitaddrev: the minimum-reviewer check still
    # runs, so reviewers have to be named even though --rmreviewers then
    # discards them and adds nothing.
    root = make_repo(tmp_path)
    run_git(root, "commit", "-q", "--amend", "-m", f"Fix\n\nReviewed-by: {STEVE}\n")

    code, _, err = addrev(root, ["--nopr", "--noself", "--rmreviewers", "steve", "levitte"])

    assert code == 0, err
    assert "Reviewed-by:" not in head_message(root)


def test_rmreviewers_alone_still_needs_the_minimum(tmp_path):
    root = make_repo(tmp_path)

    code, _, err = addrev(root, ["--nopr", "--noself", "--rmreviewers"])

    assert code == 1
    assert "Too few reviewers" in err


# -- flags ------------------------------------------------------------------


def test_trivial_flag_warns_that_it_does_nothing(tmp_path):
    root = make_repo(tmp_path)

    _, _, err = addrev(root, ["--nopr", "--noself", "--trivial", "steve", "levitte"])

    assert "--trivial has no effect" in err


def test_verbose_reports_the_chosen_reviewers(tmp_path):
    root = make_repo(tmp_path)

    _, _, err = addrev(root, ["--nopr", "--noself", "--verbose", "steve", "levitte"])

    assert STEVE in err


def test_list_shows_committers_with_a_cla(tmp_path):
    root = make_repo(tmp_path)

    code, out, _ = addrev(root, ["--list"])

    assert code == 0
    assert "steve" in out and "Steve Henson" in out
    assert "@snhenson" in out
    # No CLA and not in the commit group.
    assert "nocla" not in out


def test_listing_sorts_by_tag_then_identity(people):
    pairs = listing.list_reviewers(people)

    assert pairs == sorted(pairs, key=lambda pair: (pair[1], pair[0]))


def test_usable_identities_keeps_names_and_handles():
    record = ["steve", "steve@openssl.org", {"github": "snhenson"}, {"ghe": "sh"}]

    assert listing.usable_identities(record) == ["@sh", "@snhenson", "steve"]


# -- addrev argument grammar ------------------------------------------------


def test_a_bare_number_is_a_pr_number():
    parsed = addrev_cli.parse_args(["12345", "steve"])

    assert parsed.prnum == "12345"
    assert parsed.have_prnum


def test_an_explicit_prnum_option():
    assert addrev_cli.parse_args(["--prnum=42"]).prnum == "42"


def test_a_bare_word_is_a_reviewer():
    parsed = addrev_cli.parse_args(["--nopr", "levitte"])

    assert parsed.reviewers == ["levitte"]


def test_an_at_handle_is_a_reviewer():
    parsed = addrev_cli.parse_args(["--nopr", "@levitte"])

    assert parsed.reviewers == ["@levitte"]


def test_a_long_hex_string_is_a_commit_range():
    parsed = addrev_cli.parse_args(["--nopr", "edd05b7a1"])

    assert parsed.filter_args == "edd05b7a1"
    assert parsed.reviewers == []


def test_a_dash_number_selects_the_last_n_commits():
    assert addrev_cli.parse_args(["--nopr", "-3"]).filter_args == "HEAD~3.."


def test_the_default_range_is_the_last_commit():
    assert addrev_cli.parse_args(["--nopr"]).filter_args == "HEAD^.."


def test_an_arbitrary_range_is_taken_as_is():
    parsed = addrev_cli.parse_args(["--nopr", "abc^^..def"])

    assert parsed.filter_args == "abc^^..def"


def test_a_second_range_warns():
    parsed = addrev_cli.parse_args(["--nopr", "abc^^..def", "HEAD~2.."])

    assert parsed.filter_args == "HEAD~2.."
    assert any("overriding" in w for w in parsed.warnings)


def test_a_repository_selector_sets_the_repo():
    parsed = addrev_cli.parse_args(["--nopr", "--tools"])

    assert parsed.repo == "tools"


def test_security_implies_no_pr_number():
    parsed = addrev_cli.parse_args(["--security", "steve"])

    assert parsed.have_prnum
    assert parsed.prnum is None


def test_noself_suppresses_the_myemail_argument():
    assert addrev_cli.parse_args(["--nopr", "--noself"]).use_self is False


def test_myemail_is_captured():
    parsed = addrev_cli.parse_args(["--nopr", "--myemail=me@example.invalid"])

    assert parsed.my_email == "me@example.invalid"


def test_list_short_circuits():
    parsed = addrev_cli.parse_args(["--list", "everything", "else"])

    assert parsed.list_reviewers
    assert parsed.filter_args == "HEAD^.."


def test_help_short_circuits():
    assert addrev_cli.parse_args(["--help"]).show_help


# -- addrev execution -------------------------------------------------------


def test_a_missing_pr_number_is_refused(tmp_path):
    code, _, err = addrev(make_repo(tmp_path), ["steve"])

    assert code == 1
    assert "Need either" in err


def test_the_last_commit_is_rewritten_by_default(tmp_path):
    root = make_repo(tmp_path)

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in run_git(root, "log", "-1", "--pretty=%B")
    # The commit before it is untouched.
    assert "Reviewed-by:" not in run_git(root, "log", "-1", "--pretty=%B", "HEAD^")


def test_a_range_rewrites_every_commit_in_it(tmp_path):
    root = make_repo(tmp_path, commits=3)

    code, _, err = addrev(root, ["--nopr", "--noself", "-2", "steve", "levitte"])

    assert code == 0, err
    log = run_git(root, "log", "-2", "--pretty=%B")
    assert log.count(f"Reviewed-by: {STEVE}") == 2


def test_the_author_and_dates_survive(tmp_path):
    root = make_repo(tmp_path)
    before = run_git(root, "log", "-1", "--pretty=%an%x09%ae%x09%aI")

    addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert run_git(root, "log", "-1", "--pretty=%an%x09%ae%x09%aI") == before


def test_nothing_is_lost_the_old_tip_stays_in_the_reflog(tmp_path):
    root = make_repo(tmp_path)
    old = run_git(root, "rev-parse", "HEAD").strip()

    addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert run_git(root, "rev-parse", "HEAD").strip() != old
    assert old[:8] in run_git(root, "reflog", "--format=%H")


def test_an_annotated_tag_follows_the_rewrite_and_keeps_its_tagger(tmp_path):
    root = make_repo(tmp_path)
    run_git(root, "tag", "-a", "openssl-1.2.3", "-m", "OpenSSL 1.2.3 release tag")
    tagger_before = run_git(
        root,
        "for-each-ref",
        "--format=%(taggername)%09%(taggerdate:iso)",
        "refs/tags/openssl-1.2.3",
    )

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 0, err
    assert run_git(root, "rev-parse", "openssl-1.2.3^{commit}").strip() == (
        run_git(root, "rev-parse", "HEAD").strip()
    )
    assert "OpenSSL 1.2.3 release tag" in run_git(root, "cat-file", "tag", "openssl-1.2.3")
    assert (
        run_git(
            root,
            "for-each-ref",
            "--format=%(taggername)%09%(taggerdate:iso)",
            "refs/tags/openssl-1.2.3",
        )
        == tagger_before
    )


def test_a_tag_outside_the_range_is_untouched(tmp_path):
    root = make_repo(tmp_path, commits=3)
    run_git(root, "tag", "-a", "marker", "-m", "PRE-CLANG-FORMAT", "HEAD~2")
    before = run_git(root, "rev-parse", "marker").strip()

    addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert run_git(root, "rev-parse", "marker").strip() == before


def test_commit_targeting_leaves_other_commits_alone(tmp_path):
    root = make_repo(tmp_path, commits=3)
    target = run_git(root, "rev-parse", "HEAD").strip()

    code, _, err = addrev(
        root, ["--nopr", "--noself", f"--commit={target}", "-2", "steve", "levitte"]
    )

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in run_git(root, "log", "-1", "--pretty=%B")
    # The other commit in the range keeps its message rather than losing it.
    assert run_git(root, "log", "-1", "--pretty=%s", "HEAD^").strip() == "Commit 1"
    assert "Reviewed-by:" not in run_git(root, "log", "-1", "--pretty=%B", "HEAD^")


def test_an_unknown_reviewer_aborts_before_anything_moves(tmp_path):
    root = make_repo(tmp_path)
    old = run_git(root, "rev-parse", "HEAD").strip()

    code, _, err = addrev(root, ["--nopr", "--noself", "ghost", "steve"])

    assert code == 1
    assert "Unknown reviewers: ghost" in err
    assert run_git(root, "rev-parse", "HEAD").strip() == old


def test_nothing_is_spawned_to_compute_a_message(tmp_path):
    # The whole point: no msg-filter subprocess, so none of its plumbing.
    for gone in ("gitaddrev_command", "child_env", "LIB_DIR"):
        assert not hasattr(addrev_cli, gone)

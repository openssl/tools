# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The addrev and gitaddrev command line interfaces."""
from __future__ import annotations

import io

import pytest

from openssl_tools.reviewtools import addrev_cli, gitaddrev_cli, listing

from tests.reviewtools.helpers import LEVITTE, STEVE, FakePeople

BODY = "Fix a thing\n\nThe thing was broken.\n"


def run_gitaddrev(argv, message=BODY, env=None, people=None):
    out, err = io.StringIO(), io.StringIO()
    code = gitaddrev_cli.main(
        argv,
        stdin=io.StringIO(message),
        stdout=out,
        stderr=err,
        environ=env or {},
        query=people or FakePeople(),
    )
    return code, out.getvalue(), err.getvalue()


# -- gitaddrev --------------------------------------------------------------


def test_two_reviewers_are_added():
    code, out, _ = run_gitaddrev(["--reviewer=steve", "--reviewer=levitte"])

    assert code == 0
    assert f"Reviewed-by: {STEVE}" in out
    assert f"Reviewed-by: {LEVITTE}" in out


def test_one_reviewer_is_refused_for_the_main_repository():
    code, out, err = run_gitaddrev(["--reviewer=steve"])

    assert code == 1
    assert "Too few reviewers" in err
    assert out == ""


def test_the_author_counts_for_tools():
    code, out, _ = run_gitaddrev(
        ["--tools", "--reviewer=levitte"],
        env={"GIT_AUTHOR_EMAIL": "steve@openssl.org"},
    )

    assert code == 0
    assert f"Reviewed-by: {LEVITTE}" in out
    # An author never gets a trailer, even when they count.
    assert STEVE not in out


def test_an_unknown_reviewer_fails_the_run():
    code, _, err = run_gitaddrev(["--reviewer=ghost", "--reviewer=steve"])

    assert code == 1
    assert "Unknown reviewers: ghost" in err


def test_a_pr_number_adds_a_merged_from_line():
    _, out, _ = run_gitaddrev(
        ["--reviewer=steve", "--reviewer=levitte", "--prnum=999"]
    )

    assert out.rstrip("\n").endswith(
        "(Merged from https://github.com/openssl/openssl/pull/999)"
    )


def test_the_web_selector_names_the_web_repository():
    _, out, _ = run_gitaddrev(
        ["--web", "--reviewer=steve", "--reviewer=levitte", "--prnum=5"]
    )

    assert "https://github.com/openssl/web/pull/5)" in out


def test_release_adds_a_release_line():
    _, out, _ = run_gitaddrev(
        ["--release", "--reviewer=steve", "--reviewer=levitte"]
    )

    assert "Release: yes\n" in out


def test_rmreviewers_strips_trailers_without_adding_any():
    # Quirk carried over from gitaddrev: the minimum-reviewer check still
    # runs, so reviewers have to be named even though --rmreviewers then
    # discards them and adds nothing.
    message = f"Fix a thing\n\nReviewed-by: {STEVE}\n"

    code, out, _ = run_gitaddrev(
        ["--rmreviewers", "--reviewer=steve", "--reviewer=levitte"],
        message=message,
    )

    assert code == 0
    assert "Reviewed-by:" not in out


def test_rmreviewers_alone_still_needs_the_minimum():
    code, _, err = run_gitaddrev(["--rmreviewers"])

    assert code == 1
    assert "Too few reviewers" in err


def test_no_reviewers_at_all_is_refused():
    code, _, err = run_gitaddrev([])

    assert code == 1
    # Zero reviewers trips the minimum check before the backstop.
    assert "Too few reviewers" in err or "No reviewer set" in err


def test_a_trivial_commit_from_an_author_without_a_cla_is_allowed():
    message = "Fix a thing\n\nCLA: Trivial\n"

    code, out, _ = run_gitaddrev(
        ["--reviewer=steve", "--reviewer=levitte"],
        message=message,
        env={"GIT_AUTHOR_EMAIL": "nocla@example.invalid"},
    )

    assert code == 0
    assert f"Reviewed-by: {STEVE}" in out


def test_a_non_trivial_commit_from_an_author_without_a_cla_is_refused():
    code, _, err = run_gitaddrev(
        ["--reviewer=steve", "--reviewer=levitte"],
        env={"GIT_AUTHOR_EMAIL": "nocla@example.invalid"},
    )

    assert code == 1
    assert "has no CLA" in err


def test_trivial_flag_warns_that_it_does_nothing():
    _, _, err = run_gitaddrev(
        ["--trivial", "--reviewer=steve", "--reviewer=levitte"]
    )

    assert "--trivial has no effect" in err


def test_verbose_reports_the_chosen_reviewers():
    _, _, err = run_gitaddrev(
        ["--verbose", "--reviewer=steve", "--reviewer=levitte"]
    )

    assert "Going with these reviewers" in err
    assert STEVE in err


# -- --commit targeting -----------------------------------------------------


def test_a_targeted_commit_is_rewritten():
    code, out, _ = run_gitaddrev(
        ["--commit=abc1234", "--reviewer=steve", "--reviewer=levitte"],
        env={"GIT_COMMIT": "abc1234def5678"},
    )

    assert code == 0
    assert f"Reviewed-by: {STEVE}" in out


def test_an_untargeted_commit_passes_through_unchanged():
    # The Perl emitted nothing here, because it had already consumed stdin --
    # blanking the message of every other commit in the range.
    code, out, _ = run_gitaddrev(
        ["--commit=abc1234", "--reviewer=steve", "--reviewer=levitte"],
        env={"GIT_COMMIT": "9999999999"},
    )

    assert code == 0
    assert out == BODY


# -- --list -----------------------------------------------------------------


def test_list_shows_committers_with_a_cla():
    code, out, _ = run_gitaddrev(["--list"])

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

    assert "--prnum=12345" in parsed.gitaddrev_args
    assert parsed.have_prnum


def test_an_explicit_prnum_option():
    assert "--prnum=42" in addrev_cli.parse_args(["--prnum=42"]).gitaddrev_args


def test_a_bare_word_is_a_reviewer():
    parsed = addrev_cli.parse_args(["--nopr", "levitte"])

    assert "--reviewer=levitte" in parsed.gitaddrev_args


def test_an_at_handle_is_a_reviewer():
    parsed = addrev_cli.parse_args(["--nopr", "@levitte"])

    assert "--reviewer=@levitte" in parsed.gitaddrev_args


def test_a_long_hex_string_is_a_commit_range():
    parsed = addrev_cli.parse_args(["--nopr", "edd05b7a1"])

    assert parsed.filter_args == "edd05b7a1"
    assert not any("reviewer" in arg for arg in parsed.gitaddrev_args)


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


def test_repository_selectors_are_forwarded():
    parsed = addrev_cli.parse_args(["--nopr", "--tools"])

    assert "--tools" in parsed.gitaddrev_args


def test_security_implies_no_pr_number():
    parsed = addrev_cli.parse_args(["--security", "steve"])

    assert parsed.have_prnum
    assert not any(arg.startswith("--prnum") for arg in parsed.gitaddrev_args)


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


class RecordingRunner:
    def __init__(self, email="me@openssl.org"):
        self.commands: list[list[str]] = []
        self.email = email

    def __call__(self, argv, **kwargs):
        self.commands.append(list(argv))

        class Completed:
            returncode = 0
            stdout = self.email + "\n"

        return Completed()


def test_a_missing_pr_number_is_refused():
    err = io.StringIO()

    assert addrev_cli.main(["steve"], stderr=err, runner=RecordingRunner()) == 1
    assert "Need either" in err.getvalue()


def test_filter_branch_is_invoked_with_the_msg_filter():
    runner = RecordingRunner()

    code = addrev_cli.main(
        ["--nopr", "steve", "levitte"],
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        runner=runner,
    )

    assert code == 0
    filter_branch = runner.commands[-1]
    assert filter_branch[:3] == ["git", "filter-branch", "-f"]
    assert filter_branch[-1] == "HEAD^.."
    msg_filter = filter_branch[filter_branch.index("--msg-filter") + 1]
    assert "--reviewer=steve" in msg_filter
    assert "--reviewer=levitte" in msg_filter
    assert "--myemail=me@openssl.org" in msg_filter


def test_noself_leaves_out_the_caller():
    runner = RecordingRunner()
    addrev_cli.main(
        ["--nopr", "--noself", "steve"],
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        runner=runner,
    )

    msg_filter = " ".join(runner.commands[-1])
    assert "--myemail" not in msg_filter


def test_arguments_reaching_the_filter_are_quoted():
    runner = RecordingRunner()
    addrev_cli.main(
        ["--nopr", "--reviewer=a b; rm -rf /"],
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        runner=runner,
    )

    msg_filter = runner.commands[-1][runner.commands[-1].index("--msg-filter") + 1]
    # git runs this through a shell, so the reviewer must arrive as one word.
    assert "'--reviewer=a b; rm -rf /'" in msg_filter


def test_a_failing_filter_branch_is_reported():
    class Failing(RecordingRunner):
        def __call__(self, argv, **kwargs):
            super().__call__(argv, **kwargs)

            class Completed:
                returncode = 1
                stdout = ""

            return Completed() if argv[0] == "git" else super().__call__(argv, **kwargs)

    err = io.StringIO()
    code = addrev_cli.main(
        ["--nopr", "steve"], stdout=io.StringIO(), stderr=err, runner=Failing()
    )

    assert code == 1
    assert "addrev failed" in err.getvalue()

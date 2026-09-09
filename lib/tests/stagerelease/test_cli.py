# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Argument handling and the closing message."""

from __future__ import annotations

from pathlib import Path

import pytest

from openssl_tools.stagerelease.cli import (
    build_parser,
    format_result,
    main,
    resolve_methods,
)
from openssl_tools.stagerelease.errors import ReleaseError
from openssl_tools.stagerelease.stage import StageResult
from openssl_tools.stagerelease.tarball import Artifacts


def parse(*argv):
    return build_parser().parse_args(list(argv))


def test_no_options_means_work_it_out():
    args = parse()

    assert resolve_methods(args.next_method, args.next_beta) == ("", "")


@pytest.mark.parametrize(
    "flag,expected",
    [
        ("--alpha", ("alpha", "alpha")),
        ("--beta", ("beta", "beta")),
        ("--final", ("final", "final")),
    ],
)
def test_a_single_step_option(flag, expected):
    args = parse(flag)

    assert resolve_methods(args.next_method, args.next_beta) == expected


def test_alpha_with_next_beta():
    args = parse("--alpha", "--next-beta")

    assert resolve_methods(args.next_method, args.next_beta) == ("alpha", "beta")


def test_next_beta_alone_is_accepted():
    # The shell allowed this combination even though the usage text implied
    # otherwise; it means "work out the release, then switch to beta".
    args = parse("--next-beta")

    assert resolve_methods(args.next_method, args.next_beta) == ("", "beta")


def test_final_with_next_beta_is_rejected():
    args = parse("--final", "--next-beta")

    with pytest.raises(ReleaseError, match="Invalid combination of options"):
        resolve_methods(args.next_method, args.next_beta)


def test_step_options_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit):
        parse("--alpha", "--beta")

    assert "not allowed with" in capsys.readouterr().err


def test_reviewers_accumulate():
    args = parse("--reviewer=steve", "--reviewer=@richsalz")

    assert args.reviewers == ["steve", "@richsalz"]


def test_quiet_and_verbose_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        parse("--quiet", "--verbose")


def test_manual_prints_and_exits_cleanly(capsys):
    assert main(["--manual"]) == 0

    out = capsys.readouterr().out
    assert "stage-release - OpenSSL release staging" in out
    assert "--next-beta" in out


def test_help_mentions_every_option(capsys):
    with pytest.raises(SystemExit):
        parse("--help")

    out = capsys.readouterr().out
    for flag in [
        "--alpha",
        "--beta",
        "--final",
        "--next-beta",
        "--reviewer",
        "--quiet",
        "--verbose",
        "--debug",
        "--porcelain",
        "--manual",
    ]:
        assert flag in out


def make_result(created_branch: bool) -> StageResult:
    return StageResult(
        release="3.2.0",
        release_text="3.2.0",
        release_tag="openssl-3.2.0",
        update_branch="master",
        release_branch="openssl-3.2" if created_branch else "master",
        created_release_branch=created_branch,
        artifacts=Artifacts(
            tarball=Path("/artifacts/openssl-3.2.0.tar.gz"),
            sha1=Path("/artifacts/openssl-3.2.0.tar.gz.sha1"),
            sha256=Path("/artifacts/openssl-3.2.0.tar.gz.sha256"),
        ),
        metadata_path=Path("/artifacts/openssl-3.2.0.dat"),
        orig_head="abc123",
    )


def test_porcelain_output_is_shell_assignments():
    output = format_result(make_result(False), porcelain=True)

    assert output == "orig_head='abc123'\nmetadata='openssl-3.2.0.dat'\n"


def test_instructions_list_the_artifacts():
    output = format_result(make_result(False), porcelain=False)

    for name in [
        "openssl-3.2.0.tar.gz",
        "openssl-3.2.0.tar.gz.sha1",
        "openssl-3.2.0.tar.gz.sha256",
    ]:
        assert name in output


def test_instructions_mention_both_branches_when_one_was_created():
    output = format_result(make_result(True), porcelain=False)

    assert "Release branch: openssl-3.2" in output
    assert "Updated branch: master" in output
    # Three pushes: release branch, update branch, tag.
    assert output.count("git push") == 3


def test_instructions_mention_one_branch_otherwise():
    output = format_result(make_result(False), porcelain=False)

    assert "Release/update branch: master" in output
    assert "Release branch:" not in output
    assert output.count("git push") == 2


def test_instructions_say_nothing_was_pushed_or_shipped():
    output = format_result(make_result(False), porcelain=False)

    assert "caller's responsibility" in output


def test_an_invalid_combination_exits_nonzero(capsys):
    assert main(["--final", "--next-beta"]) == 1

    assert "Invalid combination of options" in capsys.readouterr().err


def test_running_outside_a_repository_exits_nonzero(tmp_path, monkeypatch, capsys):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    monkeypatch.chdir(outside)

    assert main([]) == 1

    assert "Not in a git worktree" in capsys.readouterr().err

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""addrev in a jj working copy.

Like the git-side execution tests in test_cli.py, these run against real
throwaway repositories, and are skipped where no jj binary is available.

The repos are colocated (`jj git init --colocate`) on purpose: that is
the shape a jj adopter's checkout actually has, and it lets `git
interpret-trailers` work unmodified.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess

import pytest

from openssl_tools.reviewtools import addrev_cli, jj, vcs
from tests.reviewtools.helpers import STEVE, FakePeople

pytestmark = pytest.mark.skipif(shutil.which("jj") is None, reason="jj is not installed")


def run_jj(cwd, *args: str) -> str:
    """Run jj in `cwd` and return its stdout, failing loudly.

    JJ_CONFIG points at nothing, so the host's own jj configuration cannot
    leak into a test; the repo-level config is set up explicitly instead.
    """
    return subprocess.run(
        ("jj", *args),
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "JJ_CONFIG": "/dev/null"},
    ).stdout


def make_jj_repo(tmp_path, commits=2, author="contributor@example.invalid"):
    """A colocated jj repo, with @ an empty commit on top of `commits` commits."""
    root = tmp_path / "repo"
    run_jj(tmp_path, "git", "init", "--colocate", "repo")
    # By default an outside contributor: has a CLA, is not a committer, and is
    # not one of the reviewers the tests name.
    run_jj(root, "config", "set", "--repo", "user.email", author)
    run_jj(root, "config", "set", "--repo", "user.name", "A Contributor")
    for n in range(commits):
        (root / f"f{n}").write_text("x\n")
        run_jj(root, "describe", "-m", f"Commit {n}\n\nBody {n}.\n")
        run_jj(root, "new")
    return root


def addrev(root, argv, people=None):
    out, err = io.StringIO(), io.StringIO()
    cwd = os.getcwd()
    # The jj subprocesses addrev spawns inherit this environment; point
    # JJ_CONFIG at nothing for the same reason run_jj does.
    old_config = os.environ.get("JJ_CONFIG")
    os.environ["JJ_CONFIG"] = "/dev/null"
    os.chdir(root)
    try:
        code = addrev_cli.main(argv, stdout=out, stderr=err, query=people or FakePeople())
    finally:
        os.chdir(cwd)
        if old_config is None:
            del os.environ["JJ_CONFIG"]
        else:
            os.environ["JJ_CONFIG"] = old_config
    return code, out.getvalue(), err.getvalue()


def description(root, rev):
    return run_jj(root, "log", "--no-graph", "-r", rev, "-T", "description")


# -- commit selection -------------------------------------------------------


def test_jj_defaults_to_the_parent_of_the_working_copy():
    assert jj.Jj().default_selection(None) == "@-"


def test_jj_dash_n_becomes_an_ancestors_revset():
    assert jj.Jj().default_selection(3) == "ancestors(@-, 3)"


def test_jj_an_explicit_selection_passes_through():
    parsed = addrev_cli.parse_args(["--nopr", "mine() & mutable()"])

    assert parsed.filter_explicit
    assert parsed.filter_args == "mine() & mutable()"


def test_jj_is_detected_in_a_jj_working_copy(tmp_path, monkeypatch):
    root = make_jj_repo(tmp_path)
    monkeypatch.chdir(root)

    assert isinstance(vcs.detect(), jj.Jj)


# -- execution --------------------------------------------------------------


def test_jj_the_last_commit_is_rewritten_by_default(tmp_path):
    root = make_jj_repo(tmp_path)

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in description(root, "@-")
    # The commit before it and the working copy are untouched.
    assert "Reviewed-by:" not in description(root, "@--")
    assert "Reviewed-by:" not in description(root, "@")


def test_jj_a_revset_rewrites_every_commit_in_it(tmp_path):
    root = make_jj_repo(tmp_path, commits=3)

    code, _, err = addrev(root, ["--nopr", "--noself", "-2", "steve", "levitte"])

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in description(root, "@-")
    assert f"Reviewed-by: {STEVE}" in description(root, "@--")
    assert "Reviewed-by:" not in description(root, "@---")


def test_jj_an_explicit_revset_is_taken_as_is(tmp_path):
    root = make_jj_repo(tmp_path, commits=2)

    code, _, err = addrev(
        root,
        ["--nopr", "--noself", "description(substring:'Commit 0')", "steve", "levitte"],
    )

    assert code == 0, err
    assert f"Reviewed-by: {STEVE}" in description(root, "@--")
    assert "Reviewed-by:" not in description(root, "@-")


def test_jj_descendants_follow_the_rewrite(tmp_path):
    # Describing a commit rebases its descendants, so the working copy ends
    # up on top of the rewritten history, still empty.
    root = make_jj_repo(tmp_path)
    at_before = run_jj(root, "log", "--no-graph", "-r", "@", "-T", "change_id")

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 0, err
    assert run_jj(root, "log", "--no-graph", "-r", "@", "-T", "change_id") == at_before
    assert "Reviewed-by:" not in description(root, "@")


# -- the safety measure -----------------------------------------------------


def test_jj_a_dirty_working_copy_is_refused(tmp_path):
    root = make_jj_repo(tmp_path)
    (root / "inflight").write_text("x\n")

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 1
    assert "not empty" in err
    assert "Reviewed-by:" not in description(root, "@-")


def test_jj_a_working_copy_that_is_not_the_tip_is_refused(tmp_path):
    root = make_jj_repo(tmp_path)
    # Both commits need a description: jj abandons an empty, undescribed
    # commit as soon as the working copy moves on, which would quietly
    # remove the child this test sets up.
    run_jj(root, "describe", "-m", "base")
    run_jj(root, "new")
    run_jj(root, "describe", "-m", "on top")
    # Back to the first empty commit, which now has a child.
    run_jj(root, "edit", "@-")

    code, _, err = addrev(root, ["--nopr", "--noself", "steve", "levitte"])

    assert code == 1
    assert "has children" in err
    assert "Reviewed-by:" not in description(root, "@")

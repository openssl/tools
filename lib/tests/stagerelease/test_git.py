# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The git wrapper, exercised against real throwaway repositories."""

from __future__ import annotations

from pathlib import Path

import pytest

from openssl_tools.stagerelease.errors import ReleaseError
from openssl_tools.stagerelease.git import Git, is_recognised_branch
from openssl_tools.stagerelease.run import Runner
from tests.stagerelease.helpers import (
    MODERN_VERSION_DAT,
    commit_all,
    init_repo,
    run_git,
)


@pytest.mark.parametrize(
    "name",
    [
        "master",
        "openssl-3.2",
        "openssl-3.0",
        "OpenSSL_1_1_1-stable",
        "OpenSSL_1_0_2u-stable",
    ],
)
def test_recognised_branches(name):
    assert is_recognised_branch(name)


@pytest.mark.parametrize(
    "name",
    ["main", "openssl-3", "feature/x", "OpenSSL_1_1_1", "openssl-3.2.1", ""],
)
def test_unrecognised_branches(name):
    assert not is_recognised_branch(name)


def test_toplevel_finds_the_worktree_root(git, modern_repo):
    assert git.toplevel().resolve() == modern_repo.resolve()


def test_toplevel_outside_a_repository(tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    git = Git(Runner(cwd=outside))

    with pytest.raises(ReleaseError, match="Not in a git worktree"):
        git.toplevel()


def test_tracks_reports_index_membership(git, modern_repo):
    assert git.tracks("VERSION.dat")
    assert not git.tracks("include/openssl/opensslv.h")

    (modern_repo / "untracked.txt").write_text("x\n")
    assert not git.tracks("untracked.txt")


def test_blob_at_head_reads_the_commit_not_the_worktree(git, modern_repo):
    (modern_repo / "VERSION.dat").write_text("MAJOR=9\n")

    assert git.blob_at_head("VERSION.dat") == MODERN_VERSION_DAT


def test_current_branch(git):
    assert git.current_branch() == "master"


def test_is_clean_and_has_tracked_changes(git, modern_repo):
    assert git.is_clean()
    assert not git.has_tracked_changes()

    # An untracked file makes the worktree dirty but is not a tracked change.
    (modern_repo / "untracked.txt").write_text("x\n")
    assert not git.is_clean()
    assert not git.has_tracked_changes()

    (modern_repo / "VERSION.dat").write_text("MAJOR=9\n")
    assert git.has_tracked_changes()
    assert git.modified_paths() == ["VERSION.dat"]


def test_commit_and_tag(git, modern_repo):
    (modern_repo / "VERSION.dat").write_text("MAJOR=9\n")
    git.add_update()
    git.commit("A change\n\nRelease: yes")
    git.tag("openssl-9.0.0", "OpenSSL 9.0.0 release tag")

    log = run_git(modern_repo, "log", "-1", "--pretty=%B")
    assert log.startswith("A change\n\nRelease: yes")
    assert "openssl-9.0.0" in run_git(modern_repo, "tag", "-l")

    # Annotated, never signed.
    assert run_git(modern_repo, "cat-file", "-t", "openssl-9.0.0").strip() == "tag"


def test_create_and_checkout_branch(git, modern_repo):
    git.create_branch("openssl-3.2")
    assert git.current_branch() == "openssl-3.2"

    git.checkout_branch("master")
    assert git.current_branch() == "master"


def test_restore_worktree_to_leaves_head_alone(git, modern_repo):
    original = (modern_repo / "VERSION.dat").read_text()
    head_before = git.head()

    (modern_repo / "VERSION.dat").write_text("MAJOR=9\n")
    git.add_update()
    git.commit("Second")
    head_after = git.head()

    git.restore_worktree_to("HEAD^")

    # Files are back to their earlier contents...
    assert (modern_repo / "VERSION.dat").read_text() == original
    # ...but the commit is still there.
    assert git.head() == head_after != head_before


def test_upstream_or_head_falls_back_to_the_commit(git):
    # No upstream is configured for this throwaway repo.
    assert git.upstream_or_head() == git.head()


def test_remote_url_passes_through_a_bare_url(git):
    assert git.remote_url("https://example.invalid/x.git") == ("https://example.invalid/x.git")
    assert git.remote_url("") == ""


def test_remote_url_resolves_a_named_remote(git, modern_repo):
    run_git(modern_repo, "remote", "add", "origin", "https://example.invalid/o.git")

    assert git.remote_url("origin") == "https://example.invalid/o.git"


def test_push_remote_reports_the_configured_remote(git, modern_repo):
    run_git(modern_repo, "remote", "add", "origin", "https://example.invalid/o.git")
    run_git(modern_repo, "config", "branch.master.remote", "origin")
    run_git(modern_repo, "config", "branch.master.merge", "refs/heads/master")

    assert git.push_remote() == "origin"


def test_changed_since_lists_touched_paths(tmp_path: Path):
    root = tmp_path / "repo"
    init_repo(root)
    (root / "old.txt").write_text("old\n")
    commit_all(root, "Old commit", when="2020-01-01T00:00:00")

    (root / "new.txt").write_text("new\n")
    (root / "old.txt").write_text("changed\n")
    commit_all(root, "New commit")

    git = Git(Runner(cwd=root))
    changed = {path: status for status, path in git.changed_since("2021-01-01")}

    assert set(changed) == {"new.txt", "old.txt"}
    assert changed["new.txt"] == "A"
    assert changed["old.txt"] == "M"


def test_changed_since_skips_deletions(tmp_path: Path):
    root = tmp_path / "repo"
    init_repo(root)
    (root / "gone.txt").write_text("x\n")
    commit_all(root, "First", when="2020-01-01T00:00:00")

    (root / "gone.txt").unlink()
    commit_all(root, "Remove it")

    git = Git(Runner(cwd=root))

    assert git.changed_since("2021-01-01") == []


def test_changed_since_with_no_earlier_commit(git):
    # Nothing precedes the cutoff, so there is no range to diff.
    assert git.changed_since("1999-01-01") == []

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""End-to-end staging, with the build system stubbed out.

This is the layer the shell version had no tests for at all: it called
./Configure and make from the middle of its logic, so exercising the branch
decisions meant building OpenSSL.  Here the build is injected.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from openssl_tools.stagerelease.errors import ReleaseError
from openssl_tools.stagerelease.git import Git
from openssl_tools.stagerelease.run import Runner
from openssl_tools.stagerelease.stage import StageOptions, stage_release
from openssl_tools.stagerelease.version.modern import parse_assignments

from tests.stagerelease.helpers import (
    CHANGES_MD,
    FAKE_MKTAR,
    LEGACY_OPENSSLV_H,
    MODERN_VERSION_DAT,
    NEWS_MD,
    TODAY,
    TODAY_TEXT,
    commit_all,
    init_repo,
    run_git,
)


class FakeBuild:
    """Records the build steps without configuring or building anything."""

    def __init__(self) -> None:
        self.calls: list[object] = []

    def configure(self) -> None:
        self.calls.append("configure")

    def update(self, *, is_alpha: bool) -> None:
        self.calls.append(("update", is_alpha))


def make_repo(tmp_path: Path, *, branch: str, patch: int, tag: str = "dev") -> Path:
    root = tmp_path / "openssl"
    init_repo(root, branch=branch)

    version = (
        MODERN_VERSION_DAT.replace("PATCH=0", f"PATCH={patch}")
        .replace("PRE_RELEASE_TAG=dev", f"PRE_RELEASE_TAG={tag}")
    )
    (root / "VERSION.dat").write_text(version)
    (root / "CHANGES.md").write_text(CHANGES_MD)
    (root / "NEWS.md").write_text(NEWS_MD)
    (root / "util").mkdir()
    mktar = root / "util" / "mktar.sh"
    mktar.write_text(FAKE_MKTAR)
    mktar.chmod(0o755)

    commit_all(root, f"Fake 3.2.{patch}-{tag}")
    return root


def stage(root: Path, **kwargs):
    runner = Runner(cwd=root)
    build = FakeBuild()
    result = stage_release(
        StageOptions(**kwargs),
        runner=runner,
        git=Git(runner),
        build=build,
        today=TODAY,
    )
    return result, build, runner


def version_on(root: Path, branch: str) -> dict[str, str]:
    return parse_assignments(run_git(root, "show", f"{branch}:VERSION.dat"))


# -- an alpha release from master -------------------------------------------


def test_alpha_from_master_creates_the_release_branch(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    result, build, _ = stage(root, next_method="alpha", next_method2="alpha")

    assert result.created_release_branch
    assert result.release_branch == "openssl-3.2"
    assert result.update_branch == "master"
    assert result.release == "3.2.0-alpha1"
    assert result.release_tag == "openssl-3.2.0-alpha1"
    assert build.calls == ["configure", ("update", True)]


def test_alpha_leaves_both_branches_in_the_right_state(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    stage(root, next_method="alpha", next_method2="alpha")

    # The release branch carries on with the alpha series...
    assert version_on(root, "openssl-3.2")["PRE_RELEASE_TAG"] == "alpha2-dev"
    assert version_on(root, "openssl-3.2")["PATCH"] == "0"
    # ...while master moves on to the next minor version.
    assert version_on(root, "master")["MINOR"] == "3"
    assert version_on(root, "master")["PRE_RELEASE_TAG"] == "dev"


def test_alpha_next_beta_switches_the_release_branch_to_beta(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    result, _, _ = stage(root, next_method="alpha", next_method2="beta")

    assert result.release_tag == "openssl-3.2.0-alpha1"
    assert version_on(root, "openssl-3.2")["PRE_RELEASE_TAG"] == "beta1-dev"


def test_the_release_tag_is_annotated_and_unsigned(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    result, _, _ = stage(root, next_method="alpha", next_method2="alpha")

    assert run_git(root, "cat-file", "-t", result.release_tag).strip() == "tag"
    contents = run_git(root, "cat-file", "tag", result.release_tag)
    assert "OpenSSL 3.2.0-alpha1 release tag" in contents
    assert "BEGIN PGP SIGNATURE" not in contents


def test_the_tag_points_at_the_release_commit(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    result, _, _ = stage(root, next_method="alpha", next_method2="alpha")

    subject = run_git(root, "log", "-1", "--pretty=%s", f"{result.release_tag}^{{}}")
    assert subject.strip() == "Prepare for release of 3.2 alpha 1"


def test_the_tagged_tree_carries_the_release_version(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    result, _, _ = stage(root, next_method="alpha", next_method2="alpha")

    tagged = parse_assignments(
        run_git(root, "show", f"{result.release_tag}^{{}}:VERSION.dat")
    )
    assert tagged["PRE_RELEASE_TAG"] == "alpha1"
    assert tagged["RELEASE_DATE"] == TODAY_TEXT


def test_release_commits_are_marked_for_release(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    stage(root, next_method="alpha", next_method2="alpha")

    log = run_git(root, "log", "--pretty=%B", "openssl-3.2")
    assert log.count("Release: yes") == 2  # the release and post-release commits


# -- artifacts --------------------------------------------------------------


def test_artifacts_land_in_the_parent_directory(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)

    result, _, _ = stage(root, next_method="alpha", next_method2="alpha")

    for path in (result.artifacts.tarball, result.artifacts.sha1, result.artifacts.sha256):
        assert path.parent == root.parent
        assert path.is_file()
    assert result.artifacts.tarball.name == "openssl-3.2.0-alpha1.tar.gz"


def test_the_metadata_file_describes_the_staging_run(tmp_path):
    root = make_repo(tmp_path, branch="master", patch=0)
    run_git(root, "remote", "add", "origin", "https://example.invalid/openssl.git")
    run_git(root, "config", "branch.master.remote", "origin")
    run_git(root, "config", "branch.master.merge", "refs/heads/master")

    result, _, _ = stage(root, next_method="alpha", next_method2="alpha")

    contents = result.metadata_path.read_text()
    assert result.metadata_path.name == "openssl-3.2.0-alpha1.dat"
    assert "update_branch='master'\n" in contents
    assert "release_branch='openssl-3.2'\n" in contents
    assert "release_tag='openssl-3.2.0-alpha1'\n" in contents
    assert "source_repo='https://example.invalid/openssl.git'\n" in contents


# -- a patch release on a release branch ------------------------------------


def test_patch_release_stays_on_the_current_branch(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)

    result, build, _ = stage(root)

    assert not result.created_release_branch
    assert result.release_branch == result.update_branch == "openssl-3.2"
    assert result.release == "3.2.1"
    assert result.release_tag == "openssl-3.2.1"
    # Not an alpha, so the symbol renumbering check is requested.
    assert build.calls == ["configure", ("update", False)]


def test_patch_release_moves_the_branch_on(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)

    stage(root)

    assert version_on(root, "openssl-3.2")["PATCH"] == "2"
    assert version_on(root, "openssl-3.2")["PRE_RELEASE_TAG"] == "dev"
    assert "openssl-3.3" not in run_git(root, "branch", "--list")


def test_patch_release_updates_the_changelogs(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)

    result, _, _ = stage(root)

    released = run_git(root, "show", f"{result.release_tag}^{{}}:CHANGES.md")
    assert f"### Changes between 3.1 and 3.2.1 [{TODAY_TEXT}]" in released

    # The post-release commit opens a fresh section.
    current = (root / "CHANGES.md").read_text()
    assert "### Changes between 3.2.1 and 3.2.2 [xx XXX xxxx]" in current
    assert " * none yet" in current
    assert f"### Changes between 3.1 and 3.2.1 [{TODAY_TEXT}]" in current


def test_a_pre_release_does_not_open_a_changelog_section(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=0, tag="beta1-dev")

    stage(root, next_method="beta", next_method2="beta")

    current = (root / "CHANGES.md").read_text()
    assert "none yet" not in current
    # NEWS.md records a pre-release without dating it.
    released = run_git(root, "show", "openssl-3.2.0-beta1^{}:NEWS.md")
    assert "[in pre-release]" in released


# -- the legacy scheme ------------------------------------------------------


def test_a_pre_3_0_branch_stages(tmp_path):
    root = tmp_path / "openssl"
    init_repo(root, branch="OpenSSL_1_0_2-stable")
    (root / "crypto").mkdir()
    (root / "crypto" / "opensslv.h").write_text(LEGACY_OPENSSLV_H)
    (root / "openssl.spec").write_text("Version:  1.0.2zg\n")
    (root / "README").write_text(" OpenSSL 1.0.2zh-dev\n\n Body.\n")
    (root / "CHANGES").write_text(
        " Changes between 1.0.2zg and 1.0.2zh [xx XXX xxxx]\n\n *)\n"
    )
    (root / "NEWS").write_text(
        "  Major changes between OpenSSL 1.0.2zg and OpenSSL 1.0.2zh"
        " [under development]\n\n      o\n"
    )
    (root / "Makefile").write_text(
        "dist:\n"
        "\t$(MAKE) $(DISTTARVARS) do-dist\n"
        "\n"
        "do-dist:\n"
        "\t@echo fake > $(TARFILE)\n"
        "\t@gzip -f $(TARFILE)\n"
    )
    commit_all(root, "Fake 1.0.2zh-dev")

    result, _, _ = stage(root)

    assert result.release == "1.0.2zh"
    assert result.release_tag == "OpenSSL_1_0_2zh"
    assert not result.created_release_branch
    # The header moved on to the next patch letter.
    assert "1.0.2zi-dev" in (root / "crypto" / "opensslv.h").read_text()
    assert (root / "openssl.spec").read_text() == "Version: 1.0.2zi\n"
    assert (root / "README").read_text().startswith(" OpenSSL 1.0.2zi-dev\n")


# -- refusals ---------------------------------------------------------------


def test_a_dirty_worktree_is_refused(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)
    (root / "CHANGES.md").write_text("edited\n")

    with pytest.raises(ReleaseError, match="Worktree is not clean"):
        stage(root)


def test_an_untracked_file_also_counts_as_dirty(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)
    (root / "scratch.txt").write_text("x\n")

    with pytest.raises(ReleaseError, match="Worktree is not clean"):
        stage(root)


def test_an_unrecognised_branch_is_refused(tmp_path):
    root = make_repo(tmp_path, branch="my-feature", patch=1)

    with pytest.raises(ReleaseError, match="Not in master or any recognised"):
        stage(root)


def test_a_released_tree_is_refused(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1, tag="")

    with pytest.raises(ReleaseError, match="Not in a development branch"):
        stage(root)


def test_a_non_openssl_worktree_is_refused(tmp_path):
    root = tmp_path / "openssl"
    init_repo(root)
    (root / "readme.txt").write_text("not openssl\n")
    commit_all(root, "Initial")

    with pytest.raises(ReleaseError, match="Couldn't find OpenSSL version data"):
        stage(root)


def test_a_patch_release_from_zero_is_refused(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=0)

    with pytest.raises(ReleaseError, match="Can't update PATCH version number from 0"):
        stage(root)


def test_a_missing_release_file_is_reported(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)
    run_git(root, "rm", "-q", "NEWS.md")
    run_git(root, "commit", "-q", "-m", "Drop NEWS.md")

    with pytest.raises(ReleaseError, match="Release file is missing"):
        stage(root)


# -- reviewers --------------------------------------------------------------


class FakePeople:
    """Stands in for reviewtools' api.openssl.org client."""

    STEVE = "Steve Henson <steve@openssl.org>"
    LEVITTE = "Richard Levitte <levitte@openssl.org>"

    def find_person_tag(self, identity, tag):
        return {
            "steve": self.STEVE,
            "steve@openssl.org": self.STEVE,
            "levitte": self.LEVITTE,
            "levitte@openssl.org": self.LEVITTE,
        }.get(identity)

    def has_cla(self, identity):
        return "openssl.org" in identity


def test_reviewers_are_credited_in_the_commit_messages(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)
    runner = Runner(cwd=root)

    stage_release(
        StageOptions(reviewers=("steve", "levitte")),
        runner=runner,
        git=Git(runner),
        build=FakeBuild(),
        today=TODAY,
        query=FakePeople(),
    )

    log = run_git(root, "log", "--pretty=%B", "-2")
    # The release commit and the post-release commit both get trailers.
    assert log.count(f"Reviewed-by: {FakePeople.STEVE}") == 2
    assert log.count(f"Reviewed-by: {FakePeople.LEVITTE}") == 2
    assert log.count("MergeDate: ") == 2
    assert log.count("Release: yes") == 2


def test_crediting_reviewers_does_not_shell_out(tmp_path):
    # The whole point of the in-process path: addrev no longer has to exist
    # on PATH for a release to be staged.
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)
    runner = Runner(cwd=root)

    stage_release(
        StageOptions(reviewers=("steve", "levitte")),
        runner=runner,
        git=Git(runner),
        build=FakeBuild(),
        today=TODAY,
        query=FakePeople(),
    )

    assert not any(argv[0] == "addrev" for argv in runner.history)


def test_an_unknown_reviewer_aborts_the_run(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)

    with pytest.raises(ReleaseError, match="Could not add reviewers"):
        stage(root, reviewers=("steve", "nosuchperson"))


def test_the_tagged_commit_carries_its_reviewers(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)
    runner = Runner(cwd=root)

    result = stage_release(
        StageOptions(reviewers=("steve", "levitte")),
        runner=runner,
        git=Git(runner),
        build=FakeBuild(),
        today=TODAY,
        query=FakePeople(),
    )

    # The tag must point at the commit that already has the trailers, or the
    # release would be tagged before it was attributed.
    tagged = run_git(root, "log", "-1", "--pretty=%B", f"{result.release_tag}^{{}}")
    assert f"Reviewed-by: {FakePeople.STEVE}" in tagged


def test_no_reviewers_means_no_trailers_and_no_lookup(tmp_path):
    root = make_repo(tmp_path, branch="openssl-3.2", patch=1)

    _, _, runner = stage(root)

    # No query object was supplied, so a lookup would have tried the
    # network; reaching the end proves none was attempted.
    assert not any(argv[0] == "addrev" for argv in runner.history)
    assert "Reviewed-by:" not in run_git(root, "log", "--pretty=%B")

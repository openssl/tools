# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Shared fixtures.

The git-backed fixtures build real (tiny) repositories rather than mocking
git out.  Nothing here needs the network and nothing configures or builds
OpenSSL, so the whole suite stays fast.
"""
from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from stagerelease.git import Git
from stagerelease.run import Runner

#: A fixed date, so nothing in the suite depends on when it runs.
TODAY = date(2026, 8, 25)
TODAY_TEXT = "25 Aug 2026"

MODERN_VERSION_DAT = """\
MAJOR=3
MINOR=2
PATCH=0
PRE_RELEASE_TAG=dev
BUILD_METADATA=
RELEASE_DATE=""
SHLIB_VERSION=3
"""

LEGACY_OPENSSLV_H = """\
# define OPENSSL_VERSION_NUMBER  0x10002210L
# ifdef OPENSSL_FIPS
#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zh-fips-dev  xx XXX xxxx"
# else
#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zh-dev  xx XXX xxxx"
# endif
# define OPENSSL_VERSION_PTEXT   " part of " OPENSSL_VERSION_TEXT
"""

CHANGES_MD = """\
Changes
=======

### Changes between 3.1 and 3.2 [xx XXX xxxx]

 * Something happened.

### Changes between 3.0 and 3.1 [14 Mar 2023]

 * Something older.
"""

NEWS_MD = """\
NEWS
====

### Major changes between OpenSSL 3.1 and OpenSSL 3.2 [under development]

  * Nothing yet.

### Major changes between OpenSSL 3.0 and OpenSSL 3.1 [14 Mar 2023]

  * Something older.
"""

#: Stands in for util/mktar.sh so the tarball step runs for real without
#: needing an OpenSSL source tree.
FAKE_MKTAR = """\
#!/bin/sh
set -e
for arg in "$@"; do
    case $arg in
        --tarfile=*) tarfile=${arg#--tarfile=} ;;
    esac
done
echo "fake openssl tarball" > "$tarfile"
gzip -f "$tarfile"
"""


def run_git(cwd: Path, *args: str, when: str | None = None) -> str:
    env = None
    if when is not None:
        # Both dates, because `git rev-list --before` filters on the committer
        # date while --date only sets the author date.
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    result = subprocess.run(
        ("git",) + args,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout


def init_repo(path: Path, branch: str = "master") -> None:
    """Create an empty repository with deterministic identity settings."""
    path.mkdir(parents=True, exist_ok=True)
    run_git(path, "init", "-q", "-b", branch)
    run_git(path, "config", "user.email", "test@openssl.org")
    run_git(path, "config", "user.name", "Test")
    run_git(path, "config", "commit.gpgsign", "false")
    run_git(path, "config", "tag.gpgsign", "false")


def commit_all(path: Path, message: str, when: str | None = None) -> None:
    run_git(path, "add", "-A")
    run_git(path, "commit", "-q", "-m", message, when=when)


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def modern_repo(tmp_path: Path) -> Path:
    """A worktree that looks like OpenSSL 3.2.0-dev on master."""
    # The worktree sits one level down so artifacts can be written to its
    # parent, as the real tool does.
    root = tmp_path / "openssl"
    init_repo(root)

    (root / "VERSION.dat").write_text(MODERN_VERSION_DAT)
    (root / "CHANGES.md").write_text(CHANGES_MD)
    (root / "NEWS.md").write_text(NEWS_MD)
    (root / "util").mkdir()
    mktar = root / "util" / "mktar.sh"
    mktar.write_text(FAKE_MKTAR)
    mktar.chmod(0o755)

    commit_all(root, "Fake 3.2.0-dev")
    return root


@pytest.fixture
def legacy_repo(tmp_path: Path) -> Path:
    """A worktree that looks like OpenSSL 1.0.2zh-dev."""
    root = tmp_path / "openssl"
    init_repo(root, branch="OpenSSL_1_0_2-stable")

    (root / "crypto").mkdir()
    (root / "crypto" / "opensslv.h").write_text(LEGACY_OPENSSLV_H)
    (root / "openssl.spec").write_text("Version:  1.0.2zh\n")
    (root / "README").write_text(" OpenSSL 1.0.2zh-dev\n\n Text follows.\n")
    (root / "CHANGES").write_text(
        " Changes between 1.0.2zg and 1.0.2zh [xx XXX xxxx]\n\n *)\n"
    )
    (root / "NEWS").write_text(
        "  Major changes between OpenSSL 1.0.2zg and OpenSSL 1.0.2zh"
        " [under development]\n\n      o\n"
    )

    commit_all(root, "Fake 1.0.2zh-dev")
    return root


@pytest.fixture
def runner(modern_repo: Path) -> Runner:
    return Runner(cwd=modern_repo)


@pytest.fixture
def git(runner: Runner) -> Git:
    return Git(runner)

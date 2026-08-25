# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The zipapp build script.

Driven as a subprocess rather than imported, because build-pyz has no .py
extension -- and because running it the way a person would is the point.
"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

LIB = Path(__file__).resolve().parents[1]
BUILD_PYZ = LIB / "build-pyz"


def run_build(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BUILD_PYZ), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_archives_are_named_like_the_scripts_they_replace(tmp_path):
    # No .pyz suffix, so one can be copied over an existing install.
    assert run_build("-o", str(tmp_path)).returncode == 0

    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["addrev", "cherry-checker", "gitaddrev", "stage-release"]
    assert all(os.access(tmp_path / name, os.X_OK) for name in names)


def test_an_extension_can_be_asked_for(tmp_path):
    assert run_build("addrev", "-e", ".pyz", "-o", str(tmp_path)).returncode == 0

    assert (tmp_path / "addrev.pyz").is_file()


def test_the_archive_carries_no_tests_or_caches(tmp_path):
    assert run_build("addrev", "-o", str(tmp_path)).returncode == 0

    with zipfile.ZipFile(tmp_path / "addrev") as archive:
        names = archive.namelist()

    assert names
    assert not any("tests" in name for name in names)
    assert not any("__pycache__" in name for name in names)


def test_the_built_archive_runs(tmp_path):
    assert run_build("cherry-checker", "-o", str(tmp_path)).returncode == 0

    result = subprocess.run(
        [str(tmp_path / "cherry-checker"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "cherry-checker" in result.stdout


def test_the_multicall_archive_dispatches_on_its_name(tmp_path):
    assert run_build("--multicall", "-o", str(tmp_path)).returncode == 0
    link = tmp_path / "cherry-checker"
    link.symlink_to("openssl-tools")

    result = subprocess.run([str(link), "--help"], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert "cherry-checker" in result.stdout


def test_the_multicall_archive_accepts_a_subcommand(tmp_path):
    assert run_build("--multicall", "-o", str(tmp_path)).returncode == 0

    result = subprocess.run(
        [str(tmp_path / "openssl-tools"), "cherry-checker", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "cherry-checker" in result.stdout


def test_an_unrecognised_name_lists_what_is_available(tmp_path):
    assert run_build("--multicall", "-o", str(tmp_path)).returncode == 0
    copy = tmp_path / "nonsense"
    copy.write_bytes((tmp_path / "openssl-tools").read_bytes())
    copy.chmod(0o755)

    result = subprocess.run([str(copy)], capture_output=True, text=True, check=False)

    output = result.stdout + result.stderr
    assert "not one of the tools in this archive" in output
    for name in ("addrev", "gitaddrev", "stage-release", "cherry-checker"):
        assert name in output

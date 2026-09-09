# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Tarball construction and checksums."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from openssl_tools.stagerelease.errors import ReleaseError
from openssl_tools.stagerelease.run import Runner
from openssl_tools.stagerelease.tarball import (
    build_tarball,
    hash_file,
    make_artifacts,
    write_checksums,
)


def test_hash_file_matches_hashlib(tmp_path: Path):
    target = tmp_path / "data"
    payload = b"openssl" * 1000
    target.write_bytes(payload)

    assert hash_file(target, "sha256") == hashlib.sha256(payload).hexdigest()
    # SHA1 is published alongside every release for historical
    # compatibility; it is a checksum here, not a security primitive.
    assert hash_file(target, "sha1") == hashlib.sha1(payload).hexdigest()  # noqa: S324


def test_hash_file_reads_more_than_one_chunk(tmp_path: Path):
    target = tmp_path / "big"
    payload = b"x" * (1024 * 1024 * 2 + 17)
    target.write_bytes(payload)

    assert hash_file(target, "sha256") == hashlib.sha256(payload).hexdigest()


def test_checksum_files_use_the_binary_mode_marker(tmp_path: Path):
    tarball = tmp_path / "openssl-3.2.0.tar.gz"
    tarball.write_bytes(b"payload")

    sha1, sha256 = write_checksums(tarball)

    assert sha1.name == "openssl-3.2.0.tar.gz.sha1"
    assert sha256.name == "openssl-3.2.0.tar.gz.sha256"
    # '<hash> *<name>' is what sha256sum emits and `sha256sum -c` reads back.
    assert sha256.read_text() == (
        f"{hashlib.sha256(b'payload').hexdigest()} *openssl-3.2.0.tar.gz\n"
    )
    assert sha1.read_text() == (
        f"{hashlib.sha1(b'payload').hexdigest()} *openssl-3.2.0.tar.gz\n"  # noqa: S324
    )


def test_checksum_files_name_the_tarball_not_its_path(tmp_path: Path):
    nested = tmp_path / "deep"
    nested.mkdir()
    tarball = nested / "openssl-3.2.0.tar.gz"
    tarball.write_bytes(b"x")

    _, sha256 = write_checksums(tarball)

    assert "deep" not in sha256.read_text()


def test_build_tarball_prefers_mktar(modern_repo: Path):
    runner = Runner(cwd=modern_repo)

    tgz = build_tarball(runner, modern_repo, "openssl-3.2.0.tar")

    assert tgz == modern_repo.parent / "openssl-3.2.0.tar.gz"
    assert tgz.is_file()
    assert runner.history[-1] == ("./util/mktar.sh", "--tarfile=../openssl-3.2.0.tar")


def test_build_tarball_falls_back_to_make_dist(modern_repo: Path):
    (modern_repo / "util" / "mktar.sh").unlink()
    # `dist` recurses with $(DISTTARVARS) on the command line, which is how
    # TARFILE actually reaches the recipe -- the same shape as OpenSSL 1.x.
    (modern_repo / "Makefile").write_text(
        "dist:\n"
        "\t$(MAKE) $(DISTTARVARS) do-dist\n"
        "\n"
        "do-dist:\n"
        "\t@echo fake > $(TARFILE)\n"
        "\t@gzip -f $(TARFILE)\n"
    )
    runner = Runner(cwd=modern_repo)

    tgz = build_tarball(runner, modern_repo, "openssl-3.2.0.tar")

    assert tgz.is_file()
    assert runner.history[-1] == (
        "make",
        "DISTTARVARS=TARFILE=../openssl-3.2.0.tar",
        "dist",
    )


def test_build_tarball_reports_a_missing_tarball(modern_repo: Path):
    # A mktar.sh that succeeds without producing anything.
    (modern_repo / "util" / "mktar.sh").write_text("#!/bin/sh\nexit 0\n")
    (modern_repo / "util" / "mktar.sh").chmod(0o755)

    with pytest.raises(ReleaseError, match="Where did the tarball end up"):
        build_tarball(Runner(cwd=modern_repo), modern_repo, "openssl-3.2.0.tar")


def test_build_tarball_reports_a_failing_builder(modern_repo: Path):
    (modern_repo / "util" / "mktar.sh").write_text("#!/bin/sh\necho boom >&2\nexit 3\n")
    (modern_repo / "util" / "mktar.sh").chmod(0o755)

    with pytest.raises(ReleaseError, match="Command failed \\(3\\)"):
        build_tarball(Runner(cwd=modern_repo), modern_repo, "openssl-3.2.0.tar")


def test_make_artifacts_removes_a_stale_signature(modern_repo: Path):
    stale = modern_repo.parent / "openssl-3.2.0.tar.gz.asc"
    stale.write_text("a signature over different bytes\n")

    artifacts = make_artifacts(Runner(cwd=modern_repo), modern_repo, "openssl-3.2.0.tar")

    assert not stale.exists()
    assert artifacts.names() == [
        "openssl-3.2.0.tar.gz",
        "openssl-3.2.0.tar.gz.sha1",
        "openssl-3.2.0.tar.gz.sha256",
    ]

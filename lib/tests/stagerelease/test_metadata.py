# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The .dat metadata file."""
from __future__ import annotations

from pathlib import Path

from openssl_tools.stagerelease.metadata import Metadata

FILES = [
    "openssl-3.2.0.tar.gz",
    "openssl-3.2.0.tar.gz.sha1",
    "openssl-3.2.0.tar.gz.sha256",
]


def test_renders_shell_variable_assignments():
    metadata = Metadata(
        update_branch="master",
        release_branch="openssl-3.2",
        release_tag="openssl-3.2.0",
        release_files=FILES,
        source_repo="git@github.openssl.org:openssl/openssl.git",
    )

    assert metadata.render() == (
        "update_branch='master'\n"
        "release_branch='openssl-3.2'\n"
        "release_tag='openssl-3.2.0'\n"
        "release_files='openssl-3.2.0.tar.gz openssl-3.2.0.tar.gz.sha1"
        " openssl-3.2.0.tar.gz.sha256'\n"
        "source_repo='git@github.openssl.org:openssl/openssl.git'\n"
    )


def test_omits_the_release_branch_when_none_was_created():
    metadata = Metadata(
        update_branch="openssl-3.2",
        release_tag="openssl-3.2.1",
        release_files=FILES,
        source_repo="https://example.invalid/openssl.git",
    )

    assert "release_branch" not in metadata.render()
    assert metadata.render().startswith("update_branch='openssl-3.2'\n")


def test_the_metadata_file_does_not_list_itself():
    metadata = Metadata(
        update_branch="master",
        release_tag="openssl-3.2.0",
        release_files=FILES,
        source_repo="x",
    )

    assert ".dat" not in metadata.render()


def test_writes_to_disk(tmp_path: Path):
    target = tmp_path / "openssl-3.2.0.dat"
    Metadata(
        update_branch="master",
        release_tag="openssl-3.2.0",
        release_files=FILES,
        source_repo="x",
    ).write(target)

    assert target.read_text().endswith("source_repo='x'\n")


def test_is_parseable_as_shell_assignments(tmp_path: Path):
    # Downstream pipeline steps source this file, so every line must be a
    # plain assignment.
    rendered = Metadata(
        update_branch="master",
        release_branch="openssl-3.2",
        release_tag="openssl-3.2.0",
        release_files=FILES,
        source_repo="x",
    ).render()

    for line in rendered.splitlines():
        name, _, value = line.partition("=")
        assert name.isidentifier()
        assert value.startswith("'") and value.endswith("'")

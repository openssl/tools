# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Building the release tarball and its checksums."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .errors import ReleaseError
from .run import Runner

#: Read the tarball in 1 MiB chunks rather than loading ~50 MiB into memory.
_CHUNK = 1024 * 1024


@dataclass
class Artifacts:
    tarball: Path
    sha1: Path
    sha256: Path

    def names(self) -> list[str]:
        return [self.tarball.name, self.sha1.name, self.sha256.name]


def hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(tarball: Path) -> tuple[Path, Path]:
    """Write <tarball>.sha1 and <tarball>.sha256 beside the tarball.

    The '*' marks binary mode, which is what sha1sum and sha256sum emit and
    what `sha256sum -c` expects to read back.
    """
    paths = []
    for algorithm in ("sha1", "sha256"):
        path = Path(f"{tarball}.{algorithm}")
        path.write_text(f"{hash_file(tarball, algorithm)} *{tarball.name}\n")
        paths.append(path)
    return paths[0], paths[1]


def build_tarball(runner: Runner, source_dir: Path, tar_name: str) -> Path:
    """Produce the gzipped release tarball in the worktree's parent directory.

    3.0+ has util/mktar.sh; older branches go through `make dist`.  Both write
    to a path relative to the source directory, which is how the artifact ends
    up one level up from the worktree.
    """
    relative = f"../{tar_name}"
    mktar = source_dir / "util" / "mktar.sh"

    if mktar.is_file():
        runner.run(["./util/mktar.sh", f"--tarfile={relative}"], echo_output=True)
    else:
        runner.run(
            ["make", f"DISTTARVARS=TARFILE={relative}", "dist"], echo_output=True
        )

    tgz = source_dir.parent / f"{tar_name}.gz"
    if not tgz.is_file():
        raise ReleaseError(f"Where did the tarball end up? ({tgz})")
    return tgz


def make_artifacts(runner: Runner, source_dir: Path, tar_name: str) -> Artifacts:
    """Build the tarball, checksum it, and clear any stale signature."""
    tgz = build_tarball(runner, source_dir, tar_name)
    sha1, sha256 = write_checksums(tgz)

    # No signature is produced here, but one left by an earlier run must not
    # survive: the tarball has just been rebuilt, so an existing .asc beside it
    # now attests to different bytes.
    stale_signature = Path(f"{tgz}.asc")
    if stale_signature.exists():
        stale_signature.unlink()

    return Artifacts(tarball=tgz, sha1=sha1, sha256=sha256)

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The .dat metadata file describing a staged release.

Written for whatever runs next in the pipeline -- signing, publishing -- so
it stays in the shell-variable-assignment form those consumers already parse.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Metadata:
    update_branch: str
    release_tag: str
    release_files: list[str]
    source_repo: str
    #: Only set when a new release branch was created for this release.
    release_branch: str | None = None

    def render(self) -> str:
        lines = [f"update_branch='{self.update_branch}'"]
        if self.release_branch:
            lines.append(f"release_branch='{self.release_branch}'")
        lines.append(f"release_tag='{self.release_tag}'")
        lines.append("release_files='{}'".format(" ".join(self.release_files)))
        lines.append(f"source_repo='{self.source_repo}'")
        return "".join(f"{line}\n" for line in lines)

    def write(self, path: Path) -> None:
        path.write_text(self.render())

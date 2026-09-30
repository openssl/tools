# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Driving the OpenSSL build system."""

from __future__ import annotations

from pathlib import Path

import pytest

from openssl_tools.stagerelease.build import Build
from openssl_tools.stagerelease.run import Runner

#: How Configure begins on each generation of branch.  1.0.2's has no #!
#: line: a shell no-op and a re-exec of perl, for a shell to find after exec
#: fails with ENOEXEC.  1.1.1 onwards has an ordinary shebang.
CONFIGURE_HEADERS = {
    "1.0.2": ":\neval 'exec perl -S $0 ${1+\"$@\"}'\n    if $running_under_some_shell;\n",
    "1.1.1": "#! /usr/bin/env perl\n# -*- mode: perl; -*-\n",
}


@pytest.mark.parametrize("branch", sorted(CONFIGURE_HEADERS))
def test_configure_runs_on_every_branch_generation(tmp_path: Path, branch: str):
    configure = tmp_path / "Configure"
    configure.write_text(CONFIGURE_HEADERS[branch] + 'print "configured for @ARGV\\n";\n')
    configure.chmod(0o755)
    lines: list[str] = []

    Build(Runner(cwd=tmp_path, log=lines.append), tmp_path).configure()

    assert lines == ["> configured for cc"]

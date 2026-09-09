# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The copyright year pass."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from openssl_tools.stagerelease.copyright_year import (
    update_copyright_years,
    update_line,
    update_text,
)
from openssl_tools.stagerelease.git import Git
from openssl_tools.stagerelease.run import Runner
from tests.stagerelease.helpers import commit_all, init_repo, run_git

NOTICE = "# Copyright {} The OpenSSL Project Authors. All Rights Reserved.\n"


def test_a_single_year_becomes_a_range():
    assert update_line(NOTICE.format("2018"), 2026) == NOTICE.format("2018-2026")


def test_an_existing_range_has_its_end_moved():
    assert update_line(NOTICE.format("2018-2023"), 2026) == NOTICE.format("2018-2026")


def test_a_range_that_collapses_is_written_as_one_year():
    # 2026-2026 would be silly, so it becomes 2026.
    assert update_line(NOTICE.format("2026"), 2026) == NOTICE.format("2026")


def test_an_up_to_date_range_is_unchanged():
    line = NOTICE.format("2018-2026")

    assert update_line(line, 2026) == line


def test_lines_without_a_notice_are_untouched():
    for line in [
        "int main(void) { return 0; }\n",
        "# Copyright 2018 Someone Else. All Rights Reserved.\n",
        "# 2018-2023 is a year range but not a copyright line\n",
    ]:
        assert update_line(line, 2026) == line


def test_only_the_first_year_range_on_a_line_moves():
    line = "# Copyright 2018 The OpenSSL Project Authors. See 1999 for details.\n"

    assert update_line(line, 2026) == (
        "# Copyright 2018-2026 The OpenSSL Project Authors. See 1999 for details.\n"
    )


def test_update_text_handles_every_line():
    text = NOTICE.format("2018") + "code\n" + NOTICE.format("2020-2021")

    assert update_text(text, 2026) == (
        NOTICE.format("2018-2026") + "code\n" + NOTICE.format("2020-2026")
    )


def test_update_text_preserves_form_feeds_and_missing_newlines():
    text = "\x0ccode\nno trailing newline"

    assert update_text(text, 2026) == text


@pytest.fixture
def copyright_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    init_repo(root)
    (root / "README").write_text(NOTICE.format("2018") + "\nA readme.\n")
    (root / "old.c").write_text(NOTICE.format("2015") + "int a;\n")
    # Backdated so this commit falls before the cutoff.
    commit_all(root, "Initial", when="2020-01-01T00:00:00")
    return root


def test_updates_files_touched_this_year_and_always_the_readme(copyright_repo):
    (copyright_repo / "new.c").write_text(NOTICE.format("2019") + "int b;\n")
    commit_all(copyright_repo, "Add new.c")

    git = Git(Runner(cwd=copyright_repo))
    result = update_copyright_years(git, copyright_repo, date(2026, 8, 25))

    assert set(result.updated) == {"new.c", "README"}
    assert (copyright_repo / "new.c").read_text().startswith(NOTICE.format("2019-2026"))
    readme = (copyright_repo / "README").read_text()
    assert readme.startswith(NOTICE.format("2018-2026"))
    # old.c was not touched this year, so it is left alone.
    assert (copyright_repo / "old.c").read_text().startswith(NOTICE.format("2015"))


def test_updated_files_are_staged(copyright_repo):
    git = Git(Runner(cwd=copyright_repo))
    update_copyright_years(git, copyright_repo, date(2026, 8, 25))

    staged = run_git(copyright_repo, "diff", "--cached", "--name-only")
    assert "README" in staged


def test_unchanged_files_keep_their_mtime(copyright_repo):
    readme = copyright_repo / "README"
    readme.write_text(NOTICE.format("2018-2026") + "\nA readme.\n")
    before = readme.stat().st_mtime_ns

    git = Git(Runner(cwd=copyright_repo))
    result = update_copyright_years(git, copyright_repo, date(2026, 8, 25))

    assert "README" not in result.updated
    assert readme.stat().st_mtime_ns == before


def test_a_path_removed_since_its_commit_is_skipped(copyright_repo):
    (copyright_repo / "temp.c").write_text(NOTICE.format("2019"))
    commit_all(copyright_repo, "Add temp.c")
    (copyright_repo / "temp.c").unlink()

    git = Git(Runner(cwd=copyright_repo))
    result = update_copyright_years(git, copyright_repo, date(2026, 8, 25))

    assert "temp.c" not in result.updated


def test_undecodable_bytes_survive(copyright_repo):
    binary = copyright_repo / "blob.bin"
    binary.write_bytes(b"\xff\xfe" + NOTICE.format("2019").encode() + b"\x80\x81")
    commit_all(copyright_repo, "Add a binary file")

    git = Git(Runner(cwd=copyright_repo))
    update_copyright_years(git, copyright_repo, date(2026, 8, 25))

    data = binary.read_bytes()
    assert data.startswith(b"\xff\xfe")
    assert data.endswith(b"\x80\x81")
    assert b"2019-2026" in data

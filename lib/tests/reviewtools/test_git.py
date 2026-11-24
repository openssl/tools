# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The git implementation of the VCS interface.

The behavioral coverage is in the execution tests in test_cli.py; what
belongs here is the git-side interface surface -- the default selection
spellings and detection.
"""

from __future__ import annotations

from openssl_tools.reviewtools import git, vcs


def test_git_default_selection_is_the_last_commit():
    assert git.Git().default_selection(None) == "HEAD^.."


def test_git_default_selection_of_the_last_n_commits():
    assert git.Git().default_selection(3) == "HEAD~3.."


def test_git_is_detected_without_a_jj_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert isinstance(vcs.detect(), git.Git)

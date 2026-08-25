# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""`cherry-checker` -- list commits eligible for cherry-picking."""
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Sequence, TextIO

from .cherry import (
    GitLog,
    format_table,
    is_openssl_repo,
    pick_cherries,
    pick_default_right,
)
from .errors import ReviewError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cherry-checker",
        description=(
            "Show the commits in 'left...right' eligible for cherry-picking."
            " A commit counts as already picked when the other side has a"
            " commit introducing an equivalent patch; see --cherry-mark in"
            " git-log(1)."
        ),
    )
    parser.add_argument(
        "left",
        nargs="?",
        default="master",
        help="the branch to compare from (default: master)",
    )
    parser.add_argument(
        "right",
        nargs="?",
        help="the branch to compare against (default: the highest local"
        " openssl-N.M branch)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="show all commits, including those already cherry-picked",
    )
    parser.add_argument(
        "-s",
        "--sort",
        action="store_true",
        help="sort by pull request number and author date",
    )
    parser.add_argument(
        "-r",
        "--remote",
        action="store_true",
        help="compare the remote branches instead of the local ones",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    git: GitLog | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    git = git or GitLog()

    try:
        if not is_openssl_repo(git):
            print(
                "cherry-checker: Not inside an openssl git repository.",
                file=stderr,
            )
            return 1

        left = args.left
        right = args.right or pick_default_right(git.branches())
        if not right:
            print(
                "cherry-checker: could not find a local openssl-N.M branch;"
                " name the branch to compare against explicitly.",
                file=stderr,
            )
            return 1

        if args.remote:
            remote = git.master_remote()
            left = f"{remote}/{left}"
            right = f"{remote}/{right}"

        commits = list(pick_cherries(git, left, right, include_picked=args.all))
        if args.sort:
            commits.sort(key=lambda entry: entry.sort_key, reverse=True)

        stdout.write(format_table(commits, left, right))
        return 0

    except ReviewError as error:
        print(f"cherry-checker: {error}", file=stderr)
        return 1
    except subprocess.SubprocessError as error:
        print(f"cherry-checker: {error}", file=stderr)
        return 1

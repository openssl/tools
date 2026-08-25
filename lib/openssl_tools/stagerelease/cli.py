# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .errors import ReleaseError
from .git import Git
from .report import Reporter
from .run import Runner
from .stage import StageOptions, StageResult, stage_release

#: next_method + next_method2 pairs that describe a coherent release.
VALID_METHOD_PAIRS = {
    ("alpha", "alpha"),
    ("alpha", "beta"),
    ("beta", "beta"),
    ("final", "final"),
    ("", ""),
    ("", "beta"),
}

PUSH_URL = "git@github.openssl.org:openssl/openssl.git"

MANUAL = """\
stage-release - OpenSSL release staging

SYNOPSIS
    stage-release [--alpha | --beta | --final] [--next-beta]
                  [--reviewer=ID ...] [--quiet | --verbose] [--debug]
                  [--porcelain]

DESCRIPTION
    Stages an OpenSSL release from the current worktree.  Run it from inside
    an OpenSSL source checkout, with the branch to release from checked out.
    It refuses to run unless that branch is master or a recognised release
    branch, and unless the worktree is clean.

    If none of --alpha, --beta or --final is given, the next release is
    worked out from the current state of the branch.

    Nothing is signed, pushed or uploaded.  The release tag is annotated but
    not signed: the signing key is held on an HSM the build host cannot
    reach, so signing the tag and the tarball happens separately, where that
    access exists.  Shipping the artifacts is the caller's job.

OPTIONS
    --alpha, --beta
        Move the branch into alpha or beta releases, or continue an ongoing
        series.  Both require PATCH to be zero.

    --next-beta
        Use with --alpha to switch to beta releases once this one is done.

    --final
        Leave the alpha or beta series and make a regular release.  Only
        valid when alpha or beta releases are ongoing.

    --reviewer=ID
        Add ID as a reviewer of the commits this makes.  May be repeated.
        Without it you have to run addrev by hand afterwards, which means
        re-tagging the release commit by hand as well.

    --quiet, --verbose, --debug
        Control how much progress output is produced.

    --porcelain
        Print the final result as shell variable assignments instead of
        instructions: orig_head and metadata.

RELEASE BRANCHES AND TAGS
    Before 3.0, release branches were named OpenSSL_<SERIES>-stable and tags
    OpenSSL_<VERSION>.  From 3.0 on, branches are openssl-<SERIES> and tags
    are openssl-<VERSION>, with -alpha<n> or -beta<n> for pre-releases.
    Both forms are recognised.

FILES
    Written to the parent directory of the worktree:

    openssl-<VERSION>.tar.gz
        The source tarball.

    openssl-<VERSION>.tar.gz.sha1, openssl-<VERSION>.tar.gz.sha256
        Its checksums, in the binary-mode format sha256sum -c reads.

    openssl-<VERSION>.dat
        Metadata for later pipeline steps, as shell variable assignments:
        update_branch, release_branch (only when one was created),
        release_tag, release_files and source_repo.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stage-release",
        description="Stage an OpenSSL release from the current worktree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "If none of --alpha, --beta or --final is given, the next release\n"
            "is worked out from the current state of the branch."
        ),
    )

    step = parser.add_mutually_exclusive_group()
    step.add_argument(
        "--alpha",
        dest="next_method",
        action="store_const",
        const="alpha",
        help='start or continue the "alpha" pre-release series',
    )
    step.add_argument(
        "--beta",
        dest="next_method",
        action="store_const",
        const="beta",
        help='start or continue the "beta" pre-release series',
    )
    step.add_argument(
        "--final",
        dest="next_method",
        action="store_const",
        const="final",
        help='leave "alpha" or "beta" and make a final release',
    )
    parser.set_defaults(next_method="")

    parser.add_argument(
        "--next-beta",
        action="store_true",
        help="switch to beta releases afterwards; use with --alpha",
    )
    parser.add_argument(
        "--reviewer",
        dest="reviewers",
        action="append",
        default=[],
        metavar="ID",
        help="reviewer of the commits made (repeatable)",
    )

    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("--quiet", action="store_true", help="only print the final output")
    noise.add_argument("--verbose", action="store_true", help="verbose output")

    parser.add_argument("--debug", action="store_true", help="include debug output")
    parser.add_argument(
        "--porcelain",
        action="store_true",
        help="print the result in an easy-to-parse form",
    )
    parser.add_argument("--manual", action="store_true", help="print the manual and exit")
    return parser


def resolve_methods(next_method: str, next_beta: bool) -> tuple[str, str]:
    """Work out the (release, post-release) pair, rejecting incoherent ones."""
    next_method2 = "beta" if next_beta else next_method
    if (next_method, next_method2) not in VALID_METHOD_PAIRS:
        raise ReleaseError(
            f"Invalid combination of options ({next_method or 'none'}, {next_method2 or 'none'})",
            "--next-beta only goes with --alpha.",
        )
    return next_method, next_method2


def format_result(result: StageResult, porcelain: bool) -> str:
    """The closing message: instructions, or parseable assignments."""
    if porcelain:
        return f"orig_head='{result.orig_head}'\nmetadata='{result.metadata_path.name}'\n"

    lines = [
        "",
        "=" * 70,
        "The release is done.  The release artifacts and a metadata file have",
        "been written to the parent directory; pushing the commits and tag and",
        "shipping the artifacts are the caller's responsibility.",
        "=" * 70,
        "",
        "The following files were generated:",
        "",
    ]
    lines += [f"    {name}" for name in result.artifacts.names()]
    lines += ["", "-" * 70, ""]

    if result.created_release_branch:
        lines += [
            "A release tag and a release branch have been added to the worktree,",
            "and the current branch has been updated.",
            "",
            f"    Updated branch: {result.update_branch}",
            f"    Release branch: {result.release_branch}",
            f"    Tag: {result.release_tag}",
            "",
            "When pushing everything to the main repository, do it like this:",
            "",
            f"    git push {PUSH_URL} \\",
            f"        {result.release_branch}",
            f"    git push {PUSH_URL} \\",
            f"        {result.update_branch}",
            f"    git push {PUSH_URL} \\",
            f"        {result.release_tag}",
        ]
    else:
        lines += [
            "A release tag has been added to the worktree, and the current branch",
            "has been updated.",
            "",
            f"    Release/update branch: {result.update_branch}",
            f"    Tag: {result.release_tag}",
            "",
            "When pushing everything to the main repository, do it like this:",
            "",
            f"    git push {PUSH_URL} \\",
            f"        {result.update_branch}",
            f"    git push {PUSH_URL} \\",
            f"        {result.release_tag}",
        ]

    lines += ["", "-" * 70]
    return "".join(f"{line}\n" for line in lines)


def main(argv: Sequence[str] | None = None, *, today: date | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.manual:
        print(MANUAL, end="")
        return 0

    reporter = Reporter(
        quiet=args.quiet,
        verbose_enabled=args.verbose,
        debug_enabled=args.debug,
    )

    try:
        next_method, next_method2 = resolve_methods(args.next_method, args.next_beta)

        runner = Runner(cwd=Path.cwd(), log=reporter.verbose)
        git = Git(runner)
        # Everything after this runs relative to the worktree root, matching
        # the shell, which cd'd there implicitly by being run from it.
        runner.cwd = git.toplevel()

        result = stage_release(
            StageOptions(
                next_method=next_method,
                next_method2=next_method2,
                reviewers=tuple(args.reviewers),
            ),
            runner=runner,
            git=git,
            reporter=reporter,
            today=today,
        )
    except ReleaseError as error:
        print(str(error), file=sys.stderr)
        return 1

    reporter.out(format_result(result, args.porcelain).rstrip("\n"))
    return 0

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""`gitaddrev` -- the git filter-branch --msg-filter side of addrev.

Reads a commit message on stdin, writes the rewritten message on stdout.
git supplies GIT_AUTHOR_EMAIL and GIT_COMMIT for the commit being rewritten.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO

from . import listing, message, reviewers
from .errors import ReviewError
from .listing import ListingSource
from .policy import POLICIES, get_policy
from .query import Query

#: Repository selectors, longest first so --help output reads sensibly.
_REPO_FLAGS = sorted(name for name in POLICIES if name != "openssl")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitaddrev",
        description="Rewrite a commit message's reviewer trailers.",
    )
    parser.add_argument("--list", action="store_true", help="list known reviewers")
    parser.add_argument("--reviewer", dest="reviewers", action="append", default=[], metavar="ID")
    parser.add_argument("--myemail", metavar="EMAIL", help="the caller's own address")
    parser.add_argument("--prnum", metavar="N", help="GitHub pull request number")
    parser.add_argument(
        "--commit",
        dest="commits",
        action="append",
        default=[],
        metavar="ID",
        help="only rewrite these commits; others pass through unchanged",
    )
    parser.add_argument(
        "--rmreviewers",
        action="store_true",
        help="strip existing Reviewed-by: lines instead of adding any",
    )
    parser.add_argument("--release", action="store_true", help="add a Release: yes line")
    parser.add_argument(
        "--trivial",
        action="store_true",
        help="accepted for compatibility; has no effect (see --help notes)",
    )
    parser.add_argument("--verbose", action="store_true")

    repo = parser.add_mutually_exclusive_group()
    for name in _REPO_FLAGS:
        repo.add_argument(
            f"--{name}",
            dest="repo",
            action="store_const",
            const=name,
            help=f"apply the {name} repository's review policy",
        )
    parser.set_defaults(repo="openssl")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
    query: ListingSource | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    environ = environ if environ is not None else os.environ
    query = query or Query()

    try:
        if args.list:
            stdout.write(listing.format_listing(listing.list_reviewers(query)))
            return 0

        policy = get_policy(args.repo)

        if args.trivial:
            # gitaddrev never implemented this; the marker has to be in the
            # commit message.  Saying so is better than silently ignoring it,
            # and better than newly weakening CLA enforcement.
            print(
                "Warning: --trivial has no effect; put 'CLA: Trivial' in the"
                " commit message instead",
                file=stderr,
            )

        original = stdin.read()
        trivial = message.is_trivial(original)
        if args.verbose and trivial:
            print("Detected trivial marker", file=stderr)

        resolution = reviewers.resolve(
            query,
            args.reviewers,
            author_email=environ.get("GIT_AUTHOR_EMAIL"),
            self_email=args.myemail,
            policy=policy,
            release=args.release,
        )
        author_email = environ.get("GIT_AUTHOR_EMAIL")
        reviewers.validate(
            resolution,
            author_email=author_email,
            policy=policy,
            trivial=trivial,
        )

        if args.verbose:
            print(
                "Going with these reviewers:\n  " + "\n  ".join(resolution.reviewers),
                file=stderr,
            )

        if args.commits and not _is_targeted(environ.get("GIT_COMMIT"), args.commits):
            # Not one of the commits asked for, so pass it through untouched.
            # The Perl tried to do this by draining stdin, which it had
            # already consumed -- so it emitted nothing and blanked the
            # message of every other commit in the range.
            stdout.write(original)
            return 0

        if not args.rmreviewers:
            reviewers.require_any(resolution.reviewers)

        stdout.write(
            message.rewrite(
                original,
                reviewers=resolution.reviewers,
                repo=policy.name,
                prnum=args.prnum,
                release=args.release,
                remove_reviewers=args.rmreviewers,
            )
        )
        return 0

    except ReviewError as error:
        print(str(error), file=stderr)
        return 1


def _is_targeted(commit_id: str | None, wanted: Sequence[str]) -> bool:
    """Whether GIT_COMMIT is one of the commits named by --commit.

    Matching is by prefix, so an abbreviated id works.
    """
    if not commit_id:
        return False
    return any(commit_id.startswith(candidate) for candidate in wanted)


if __name__ == "__main__":
    sys.exit(main())

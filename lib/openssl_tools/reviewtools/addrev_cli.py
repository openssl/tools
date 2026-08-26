# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""`addrev` -- add reviewer trailers to a range of commits.

The argument grammar is positional and forgiving, because it is typed by
hand and forwarded verbatim from ghmerge.  A bare number is a PR number, a
bare word is a reviewer, a word that looks like an object id is a commit
range, and `-3` means the last three commits.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TextIO

from . import listing, message, reviewers, rewrite
from .commands import CommandRunner, run_command
from .errors import ReviewError
from .policy import POLICIES, get_policy
from .query import Query

USAGE = """\
usage: addrev args...

option style arguments:

--help                 Print this help and exit
--list                 List the known reviewers and exit (discards all other arguments)
--verbose              Be a bit more verbose
--trivial              Accepted for compatibility; has no effect.  Put
                       'CLA: Trivial' in the commit message instead.
--reviewer=<reviewer>  A reviewer to be added on a Reviewed-by: line
--rmreviewers          Remove all existing Reviewed-by: lines before adding reviewers
--commit=<id>          Only apply to commit <id>
--myemail=<email>      Set email address.
                       Defaults to the result from git configuration setting user.email
--noself               Do not add your own address as a possible reviewer
--nopr                 Do not require a PR number
--security             Merge into the security repo; implies --nopr
[--prnum=]NNN          Add a reference to GitHub pull request NNN
-<n>                   Change the last <n> commits.  Defaults to 1

repository selectors (default: openssl):

{repos}

non-option style arguments can be:

a string of alphanumeric or '-' characters, denoting a reviewer name.

a string starting with @, denoting a reviewer's github ID.

anything else will be used as a commit range.  If no commit range is given,
HEAD^.. is assumed.

Examples (all meaning the same thing):

  addrev 12345 -2 steve levitte
  addrev --prnum=12345 steve @levitte HEAD^^..
  addrev 12345 --reviewer=steve --reviewer=levitte@openssl.org -2
"""

_PRNUM_RE = re.compile(r"^(?:--prnum=)?(\d{1,6})$")
_BARE_WORD_RE = re.compile(r"^\w[-\w]*$")
_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{7,}")
_LAST_N_RE = re.compile(r"^-(\d+)$")
_REVIEWER_OPT_RE = re.compile(r"^--reviewer=(.+)$")
_MYEMAIL_RE = re.compile(r"^--myemail=(.+)$")
_COMMIT_RE = re.compile(r"^--commit=(.+)$")


@dataclass
class Invocation:
    """What a command line asked for."""

    reviewers: list[str] = field(default_factory=list)
    prnum: str | None = None
    commits: list[str] = field(default_factory=list)
    repo: str = "openssl"
    release: bool = False
    remove_reviewers: bool = False
    trivial: bool = False
    verbose: bool = False
    filter_args: str = ""
    have_prnum: bool = False
    use_self: bool = True
    my_email: str | None = None
    list_reviewers: bool = False
    show_help: bool = False
    warnings: list[str] = field(default_factory=list)


def parse_args(argv: Sequence[str]) -> Invocation:
    result = Invocation()

    def set_filter(value: str) -> None:
        if result.filter_args:
            result.warnings.append(f"Warning: overriding previous filter args {result.filter_args}")
        result.filter_args = value

    for arg in argv:
        prnum = _PRNUM_RE.match(arg)
        if prnum:
            result.prnum = prnum.group(1)
            result.have_prnum = True
            continue

        if arg.startswith("@"):
            result.reviewers.append(arg)
            continue

        if _BARE_WORD_RE.match(arg):
            # A long hex string is an object id, not somebody's name.
            if _OBJECT_ID_RE.match(arg):
                set_filter(arg)
            else:
                result.reviewers.append(arg)
            continue

        reviewer = _REVIEWER_OPT_RE.match(arg)
        if reviewer:
            result.reviewers.append(reviewer.group(1))
            continue

        if arg == "--rmreviewers":
            result.remove_reviewers = True
            continue

        if arg == "--trivial":
            result.trivial = True
            continue

        if arg == "--verbose":
            result.verbose = True
            continue

        if arg == "--release":
            result.release = True
            continue

        if arg.startswith("--") and arg[2:] in POLICIES:
            result.repo = arg[2:]
            continue

        if arg == "--noself":
            result.use_self = False
            continue

        my_email = _MYEMAIL_RE.match(arg)
        if my_email:
            result.my_email = my_email.group(1)
            continue

        if arg in ("--nopr", "--security"):
            # Neither needs a PR reference: --nopr says so outright, and the
            # security repo's commits do not carry one.
            result.have_prnum = True
            continue

        commit = _COMMIT_RE.match(arg)
        if commit:
            result.commits.append(commit.group(1))
            continue

        last_n = _LAST_N_RE.match(arg)
        if last_n:
            set_filter(f"HEAD~{last_n.group(1)}..")
            continue

        if arg == "--list":
            result.list_reviewers = True
            break

        if arg in ("--help", "-h"):
            result.show_help = True
            break

        set_filter(arg)

    if not result.filter_args:
        result.filter_args = "HEAD^.."

    return result


def rewrite_range(
    invocation: Invocation,
    *,
    query: reviewers.PersonSource,
    stderr: TextIO,
    runner: CommandRunner = run_command,
) -> int:
    """Rewrite the messages of every commit in the range.

    Reviewer resolution is per commit, because the author affects it -- the
    CLA check and whether the author counts towards the total.  Results are
    cached by author, so a range of commits by one person costs one round of
    lookups.
    """
    policy = get_policy(invocation.repo)
    commits = rewrite.read_range(invocation.filter_args, runner=runner)
    if not commits:
        print("No commits in range", file=stderr)
        return 0

    ref = rewrite.current_branch_ref(runner=runner)
    old_tip = commits[-1].sha
    resolutions: dict[str | None, reviewers.Resolution] = {}

    def transform(commit: rewrite.CommitInfo) -> str:
        # A commit the caller did not ask for passes through untouched.
        if invocation.commits and not any(
            commit.sha.startswith(wanted) for wanted in invocation.commits
        ):
            return commit.message

        author = commit.author_email or None
        if author not in resolutions:
            resolutions[author] = reviewers.resolve(
                query,
                invocation.reviewers,
                author_email=author,
                self_email=invocation.my_email,
                policy=policy,
                release=invocation.release,
            )
        resolution = resolutions[author]

        reviewers.validate(
            resolution,
            author_email=author,
            policy=policy,
            trivial=message.is_trivial(commit.message),
        )
        if not invocation.remove_reviewers:
            reviewers.require_any(resolution.reviewers)

        if invocation.verbose:
            print(
                f"{commit.sha[:12]} reviewed-by " + ", ".join(resolution.reviewers),
                file=stderr,
            )

        return message.rewrite(
            commit.message,
            reviewers=resolution.reviewers,
            repo=policy.name,
            prnum=invocation.prnum,
            release=invocation.release,
            remove_reviewers=invocation.remove_reviewers,
        )

    mapping = rewrite.replay(commits, transform, runner=runner)
    new_tip = mapping[old_tip]
    if new_tip == old_tip:
        print("Nothing to rewrite", file=stderr)
        return 0

    rewrite.update_branch(ref, new_tip, old_tip, runner=runner)
    for name in rewrite.repoint_tags(mapping, runner=runner):
        print(f"Moved tag {name}", file=stderr)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    runner: CommandRunner = run_command,
    query: listing.ListingSource | None = None,
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    invocation = parse_args(argv)
    for warning in invocation.warnings:
        print(warning, file=stdout)

    if invocation.show_help:
        print(USAGE.format(repos=_format_repos()), file=stderr)
        return 0

    try:
        query = query or Query()

        if invocation.list_reviewers:
            stdout.write(listing.format_listing(listing.list_reviewers(query)))
            return 0

        if not invocation.have_prnum:
            raise ReviewError("Need either [--prnum=]NNN or --nopr flag")

        if invocation.use_self and not invocation.my_email:
            invocation.my_email = _git_user_email(runner)

        if invocation.trivial:
            print(
                "Warning: --trivial has no effect; put 'CLA: Trivial' in the"
                " commit message instead",
                file=stderr,
            )

        return rewrite_range(invocation, query=query, runner=runner, stderr=stderr)

    except ReviewError as error:
        print(str(error), file=stderr)
        return 1


def _git_user_email(runner: CommandRunner) -> str | None:
    completed = runner(
        ["git", "config", "--get", "user.email"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return (completed.stdout or "").strip() or None


def _format_repos() -> str:
    return "\n".join(
        f"--{name:<20} {policy.min_reviewers} reviewer(s)"
        f"{', author counts' if policy.min_authors else ''}"
        for name, policy in sorted(POLICIES.items())
    )

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""`addrev` -- run gitaddrev over a range of commits.

The argument grammar is positional and forgiving, because it is typed by
hand and forwarded verbatim from ghmerge.  A bare number is a PR number, a
bare word is a reviewer, a word that looks like an object id is a commit
range, and `-3` means the last three commits.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from .commands import CommandRunner, run_command
from .errors import ReviewError
from .policy import POLICIES

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

#: Flags forwarded to gitaddrev untouched.
_PASSTHROUGH = {"--rmreviewers", "--trivial", "--verbose", "--release"}


@dataclass
class Invocation:
    """What a command line asked for."""

    gitaddrev_args: list[str] = field(default_factory=list)
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
            result.gitaddrev_args.append(f"--prnum={prnum.group(1)}")
            result.have_prnum = True
            continue

        if arg.startswith("@"):
            result.gitaddrev_args.append(f"--reviewer={arg}")
            continue

        if _BARE_WORD_RE.match(arg):
            # A long hex string is an object id, not somebody's name.
            if _OBJECT_ID_RE.match(arg):
                set_filter(arg)
            else:
                result.gitaddrev_args.append(f"--reviewer={arg}")
            continue

        reviewer = _REVIEWER_OPT_RE.match(arg)
        if reviewer:
            result.gitaddrev_args.append(f"--reviewer={reviewer.group(1)}")
            continue

        if arg in _PASSTHROUGH:
            result.gitaddrev_args.append(arg)
            continue

        if arg.startswith("--") and arg[2:] in POLICIES:
            result.gitaddrev_args.append(arg)
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
            result.gitaddrev_args.append(f"--commit={commit.group(1)}")
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


#: The directory holding the openssl_tools package, so a child process can
#: import it.  Derived from this file rather than from a sibling directory:
#: the package locates its own root, and nothing outside it.
LIB_DIR = Path(__file__).resolve().parents[2]


def gitaddrev_command() -> list[str]:
    """How to invoke gitaddrev, honouring the GITADDREV override.

    Runs the module rather than looking for the `gitaddrev` script, so this
    works regardless of where that script lives or whether it is on PATH.
    """
    override = os.environ.get("GITADDREV")
    if override:
        return shlex.split(override)
    return [sys.executable, "-m", "openssl_tools.reviewtools.gitaddrev_cli"]


def child_env() -> dict[str, str]:
    """The environment for git filter-branch and the msg-filter it spawns."""
    existing = os.environ.get("PYTHONPATH")
    return {
        **os.environ,
        "FILTER_BRANCH_SQUELCH_WARNING": "1",
        # git runs the msg-filter through a shell, so openssl_tools has to be
        # importable there too.
        "PYTHONPATH": (f"{LIB_DIR}{os.pathsep}{existing}" if existing else str(LIB_DIR)),
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    runner: CommandRunner = run_command,
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

    base = gitaddrev_command()

    if invocation.list_reviewers:
        return runner([*base, "--list"]).returncode

    try:
        if not invocation.have_prnum:
            raise ReviewError("Need either [--prnum=]NNN or --nopr flag")

        args = list(invocation.gitaddrev_args)
        if invocation.use_self:
            email = invocation.my_email or _git_user_email(runner)
            if email:
                args.append(f"--myemail={email}")

        filter_command = " ".join(shlex.quote(part) for part in base + args)
        env = child_env()
        completed = runner(
            [
                "git",
                "filter-branch",
                "-f",
                "--tag-name-filter",
                "cat",
                "--msg-filter",
                filter_command,
                invocation.filter_args,
            ],
            env=env,
        )
        if completed.returncode != 0:
            raise ReviewError("addrev failed")
        return 0

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

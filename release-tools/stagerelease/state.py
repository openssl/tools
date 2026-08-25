# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""The release state machine -- a port of release-aux/release-state-fn.sh.

`next_release_state` is a pure function: state in, state out, with the date
injected.  That is the whole point of separating it from the orchestration --
every transition below is reachable in a unit test without a git repository.

The phases a worktree can be in (the shell's "$PRE_LABEL$TYPE"):

    ''          released
    'dev'       in development, the normal state of a branch
    'alpha'     an alpha release was just made
    'alphadev'  alpha releases are ongoing, next one in development
    'beta'      a beta release was just made
    'betadev'   beta releases are ongoing, next one in development

Each staging run applies two transitions: one to move the tree *to* the
release being made, and one to move it on to the next development state.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from .errors import ReleaseError
from .version import ReleaseState, Scheme

#: The `next` values a caller may ask for.
NEXT_METHODS = ("", "alpha", "beta", "final", "minor")

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def format_release_date(when: date) -> str:
    """Format a release date the way OpenSSL's release files spell it.

    The shell used `date '+%-d %b %Y'` under LC_ALL=C -- day without a
    leading zero, abbreviated English month.  The month table is spelled out
    here rather than using strftime('%b') so the result cannot drift with the
    process locale.
    """
    return f"{when.day} {_MONTHS[when.month - 1]} {when.year}"


def next_release_state(
    scheme: Scheme,
    state: ReleaseState,
    next_method: str,
    today: date,
) -> ReleaseState:
    """Return the state that follows `state` when asked for `next_method`.

    Raises ReleaseError for transitions that make no sense, e.g. an alpha
    release from a branch that is already in beta.
    """
    if next_method not in NEXT_METHODS:
        raise ValueError(f"unknown next method: {next_method!r}")

    date_string = format_release_date(today)

    # The shell retried once, rewriting an empty `next` into 'alpha' or 'beta'
    # when the branch was already in one of those series.  Two iterations is
    # always enough; the bound guards against a future edit reintroducing a
    # cycle.
    for _ in range(2):
        phase = state.phase

        # -- alpha releases -------------------------------------------------
        if next_method == "alpha":
            if phase.startswith("beta") or phase == "":
                raise ReleaseError(
                    "Invalid state for an alpha release",
                    "Try --beta or --final, or perhaps nothing",
                )
            if phase in ("dev", "alphadev"):
                return _release(scheme, state, "alpha", date_string)
            if phase == "alpha":
                return _post_release(scheme, state, "alpha")

        # -- beta releases --------------------------------------------------
        elif next_method == "beta":
            if phase == "":
                raise ReleaseError(
                    "Invalid state for beta release",
                    "Try --final, or perhaps nothing",
                )
            if phase in ("dev", "alphadev", "betadev"):
                return _release(scheme, state, "beta", date_string)
            # 'alpha' lands here too: --next-beta switches an alpha series
            # over to beta during the post-release step.
            if phase in ("beta", "alpha"):
                return _post_release(scheme, state, "beta")

        # -- final releases -------------------------------------------------
        elif next_method == "final":
            if phase == "dev":
                raise ReleaseError(
                    "Invalid state for final release",
                    "This should have been preceded by an alpha or a beta release",
                )
            if phase in ("alphadev", "betadev"):
                return _release(scheme, state, "final", date_string)
            if phase == "":
                return _post_release(scheme, state, "final")

        # -- moving master on to the next minor version ----------------------
        elif next_method == "minor":
            return _post_release(scheme, state, "minor")

        # -- whatever comes next --------------------------------------------
        else:
            if phase == "":
                return _post_release(scheme, state, "")
            if phase == "dev":
                if state.patch in (0, ""):
                    raise ReleaseError(
                        "Can't update PATCH version number from 0",
                        "Please use --alpha or --beta",
                    )
                return _release(scheme, state, "", date_string)
            # Already in an alpha or beta series: carry on with it, as though
            # the caller had said so explicitly.
            if phase.startswith("alpha"):
                next_method = "alpha"
                continue
            if phase.startswith("beta"):
                next_method = "beta"
                continue

        raise ReleaseError("Invalid combination of options")

    raise ReleaseError("Invalid combination of options")


def _release(
    scheme: Scheme, state: ReleaseState, kind: str, date_string: str
) -> ReleaseState:
    """Move to a released state: stamp the date and drop the -dev marker."""
    return scheme.bump(replace(state, dev=False, release_date=date_string), kind)


def _post_release(scheme: Scheme, state: ReleaseState, kind: str) -> ReleaseState:
    """Move back into development: clear the date and restore the -dev marker."""
    return scheme.bump(replace(state, dev=True, release_date=""), kind)

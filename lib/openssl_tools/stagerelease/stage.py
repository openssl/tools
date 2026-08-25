# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Staging a release, end to end -- a port of stage-release.sh.

The run produces, in the current worktree:

  * a copyright-year commit, if anything needed updating
  * a `make update` commit, if anything needed updating
  * a release commit and an annotated (never signed) tag
  * a post-release commit returning the branch to development
  * when releasing from master at PATCH == 0, a new release branch, and a
    further commit moving master on to the next minor version

and, in the worktree's parent directory, the tarball, its checksums, and a
metadata file describing what was staged.

Nothing is signed, pushed or uploaded here.  The signing key lives on an HSM
the build host cannot reach, so that is a separate step run elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..reviewtools import PersonSource
from . import reviewers
from .build import Build, BuildSystem
from .copyright_year import update_copyright_years
from .errors import ReleaseError
from .fixups import FIXUPS, POSTRELEASE, RELEASE, FixupContext, get_fixup
from .git import Git, is_recognised_branch
from .metadata import Metadata
from .report import Reporter
from .run import Runner
from .state import next_release_state
from .tarball import Artifacts, make_artifacts
from .textutil import read_text, write_text
from .version import ReleaseState, Scheme, detect_scheme


@dataclass(frozen=True)
class StageOptions:
    """What the caller asked for."""

    #: '', 'alpha', 'beta' or 'final' -- the release being made now.
    next_method: str = ""
    #: The state to leave the branch in afterwards.  Differs from
    #: `next_method` only for --alpha --next-beta.
    next_method2: str = ""
    reviewers: tuple[str, ...] = ()


@dataclass
class StageResult:
    """What the run produced."""

    release: str
    release_text: str
    release_tag: str
    update_branch: str
    release_branch: str
    created_release_branch: bool
    artifacts: Artifacts
    metadata_path: Path
    orig_head: str


def release_text_for(scheme: Scheme, state: ReleaseState) -> str:
    """How a release names itself in commit messages and changelogs."""
    if state.pre_label:
        return _pre_release_text(scheme, state)
    return scheme.full_version(state)


def postrelease_text_for(scheme: Scheme, state: ReleaseState) -> str:
    """As above, for the post-release commit.

    Note this falls back to the plain version, not the full version: the
    post-release state carries a '-dev' tag that does not belong in the text.
    """
    if state.pre_label:
        return _pre_release_text(scheme, state)
    return f"{scheme.version(state)}{state.marked_build_metadata}"


def _pre_release_text(scheme: Scheme, state: ReleaseState) -> str:
    return f"{scheme.series(state)}{state.marked_build_metadata} {state.pre_label} {state.pre_num}"


def check_fixups_available(scheme: Scheme) -> None:
    """Fail early if any release file has no fixup for it.

    The shell checked that the corresponding .pl files existed on disk; the
    equivalent now is that the registry has an entry.
    """
    missing = [
        f"{name} ({direction})"
        for name in scheme.release_files
        for direction in (RELEASE, POSTRELEASE)
        if (name, direction) not in FIXUPS
    ]
    if missing:
        raise ReleaseError("No fixup defined for: " + ", ".join(missing))


def write_version(scheme: Scheme, root: Path, state: ReleaseState) -> None:
    path = root / scheme.version_file
    current = read_text(path) if path.is_file() else ""
    write_text(path, scheme.render(state, current))


def apply_fixups(
    root: Path,
    scheme: Scheme,
    direction: str,
    ctx: FixupContext,
    reporter: Reporter,
) -> None:
    for name in scheme.release_files:
        path = root / name
        if not path.is_file():
            raise ReleaseError(f"Release file is missing: {path}")
        reporter.verbose(f"> {name}")
        text = read_text(path)
        write_text(path, get_fixup(name, direction)(text, ctx))


def stage_release(
    options: StageOptions,
    *,
    runner: Runner,
    git: Git,
    build: BuildSystem | None = None,
    reporter: Reporter | None = None,
    today: date | None = None,
    query: PersonSource | None = None,
) -> StageResult:
    """Stage a release in the worktree `git` points at."""
    reporter = reporter or Reporter()
    today = today or date.today()

    # -- checks -------------------------------------------------------------

    root = git.toplevel()
    build = build or Build(runner, root)
    scheme = detect_scheme(git)
    check_fixups_available(scheme)

    orig_branch = git.current_branch()
    if not is_recognised_branch(orig_branch):
        raise ReleaseError(
            "Not in master or any recognised release branch",
            "Please 'git checkout' an appropriate branch",
        )

    orig_remote_url = git.remote_url(git.push_remote())
    orig_head = git.upstream_or_head()

    reporter.echo("== Initializing work tree")

    # The run operates on the current branch directly, so a dirty worktree
    # would end up inside the release commit.
    if not git.is_clean():
        raise ReleaseError("Worktree is not clean; refusing to run")

    state = scheme.parse(git.blob_at_head(scheme.version_file))
    reporter.debug(f"initial state = {state}")

    if not state.dev:
        raise ReleaseError(
            "Not in a development branch.",
            "Have a look at the git log, it may be that a previous crash left\n"
            "it in an intermediate state and that need to drop the top commit:\n"
            "\n"
            f"    git reset --hard {orig_head}\n"
            "    # WARNING! LOOK BEFORE YOU ACT, KNOW WHAT YOU DO",
        )

    # -- branch layout ------------------------------------------------------

    update_branch = orig_branch
    release_branch = scheme.branch_name(state)

    # A new release branch is created only when releasing from master at
    # PATCH == 0.  Otherwise -- already on a release branch, or this is a
    # patch release -- the release commit goes on the current branch.
    patch_is_zero = state.patch in (0, "")
    created_release_branch = release_branch != update_branch and patch_is_zero
    if not created_release_branch:
        release_branch = update_branch

    # -- decide the release ------------------------------------------------

    release_state = next_release_state(scheme, state, options.next_method, today)
    release_tag = scheme.tag_name(release_state)
    reporter.debug(f"release state = {release_state}")
    reporter.debug(f"release tag = {release_tag}")

    # -- reviewers ----------------------------------------------------------

    # Deliberately the last check, and the first thing that touches the
    # network: every local sanity check above is instant, and none of the
    # work below is cheap.  A reviewer who turns out not to be a committer
    # must not cost the caller a copyright commit and a `make update` first.
    reviewer_tags = reviewers.resolve(git, options.reviewers, query=query)
    if reviewer_tags:
        reporter.verbose("== Reviewed-by: " + ", ".join(reviewer_tags))

    # -- copyright years ----------------------------------------------------

    reporter.verbose("== Checking source file copyright year updates")
    result = update_copyright_years(git, root, today, reporter.verbose)
    reporter.verbose(f"== Files considered: {result.considered}")
    if git.has_tracked_changes():
        reporter.verbose("== Committing copyright year updates")
        git.add_update()
        git.commit("Copyright year updates\n\nRelease: yes")
        reviewers.credit(git, reviewer_tags)

    # -- make update --------------------------------------------------------

    reporter.echo("== Configuring OpenSSL for update and release.  This may take a bit of time")
    build.configure()

    reporter.verbose("== Checking source file updates and fips checksums")
    build.update(is_alpha=options.next_method == "alpha")

    if git.has_tracked_changes():
        reporter.verbose("== Committing updates")
        git.add_update()
        git.commit("make update\n\nRelease: yes")
        reviewers.credit(git, reviewer_tags)

    # -- the release commit -------------------------------------------------

    if created_release_branch:
        reporter.verbose(f"== Creating a local release branch and switch to it: {release_branch}")
        git.create_branch(release_branch)

    write_version(scheme, root, release_state)

    release = scheme.full_version(release_state)
    release_text = release_text_for(scheme, release_state)
    reporter.verbose(f"== Updated version information to {release}")

    reporter.verbose(
        f"== Updating files with release date for {release} : {release_state.release_date}"
    )
    apply_fixups(
        root,
        scheme,
        RELEASE,
        FixupContext(
            release=release,
            release_text=release_text,
            release_date=release_state.release_date,
        ),
        reporter,
    )

    reporter.verbose("== Committing updates and tagging")
    git.add_update()
    git.commit(f"Prepare for release of {release_text}\n\nRelease: yes")
    reviewers.credit(git, reviewer_tags)

    reporter.echo(f"Tagging release with tag {release_tag}.")
    git.tag(release_tag, f"OpenSSL {release} release tag")

    # -- artifacts ----------------------------------------------------------

    tar_name = f"openssl-{release}.tar"
    reporter.echo("== Generating tar, hash, and metadata files.")
    reporter.echo("== This may take a bit of time...")
    reporter.verbose(f"== Making tarfile: {tar_name}.gz")
    artifacts = make_artifacts(runner, root, tar_name)

    metadata_path = root.parent / f"openssl-{release}.dat"
    reporter.verbose(f"== Generating metadata file: {metadata_path.name}")
    Metadata(
        update_branch=orig_branch,
        release_branch=scheme.branch_name(state) if created_release_branch else None,
        release_tag=release_tag,
        release_files=artifacts.names(),
        source_repo=orig_remote_url,
    ).write(metadata_path)

    # -- the post-release commit --------------------------------------------

    # Put every tracked file back to its pre-release contents without
    # touching HEAD, so the post-release fixups start from the same text the
    # release fixups did.  That is what lets one set of post-release fixups
    # serve both the release branch and the update branch.
    reporter.verbose("== Reset all files to their pre-release contents")
    git.restore_worktree_to("HEAD^")

    prev_release_text = release_text
    prev_release_date = release_state.release_date

    post_state = next_release_state(scheme, release_state, options.next_method2, today)
    write_version(scheme, root, post_state)

    post_release = scheme.full_version(post_state)
    post_text = postrelease_text_for(scheme, post_state)
    reporter.verbose(f"== Updated version information to {post_release}")

    reporter.verbose(f"== Updating files for {post_release} :")
    apply_fixups(
        root,
        scheme,
        POSTRELEASE,
        FixupContext(
            release=post_release,
            release_text=post_text,
            prev_release_text=prev_release_text,
            prev_release_date=prev_release_date,
        ),
        reporter,
    )

    reporter.verbose("== Committing updates")
    git.add_update()
    git.commit(f"Prepare for {post_text}\n\nRelease: yes")
    reviewers.credit(git, reviewer_tags)

    # -- move the update branch on to the next minor version ----------------

    if created_release_branch:
        reporter.verbose(f"== Going back to the update branch {update_branch}")
        git.checkout_branch(update_branch)

        update_state = scheme.parse(git.blob_at_head(scheme.version_file))
        minor_state = next_release_state(scheme, update_state, "minor", today)
        write_version(scheme, root, minor_state)

        minor_release = scheme.full_version(minor_state)
        minor_text = f"{scheme.series(minor_state)}{minor_state.marked_build_metadata}"
        reporter.verbose(f"== Updated version information to {minor_release}")

        reporter.verbose(f"== Updating files for {minor_release} :")
        apply_fixups(
            root,
            scheme,
            POSTRELEASE,
            # No previous release is named here, so the fixups fall back to
            # their placeholder text.
            FixupContext(release=minor_release, release_text=minor_text),
            reporter,
        )

        reporter.verbose("== Committing updates")
        git.add_update()
        git.commit(f"Prepare for {minor_text}\n\nRelease: yes")
        reviewers.credit(git, reviewer_tags)

    reporter.verbose("== Done")

    return StageResult(
        release=release,
        release_text=release_text,
        release_tag=release_tag,
        update_branch=update_branch,
        release_branch=release_branch,
        created_release_branch=created_release_branch,
        artifacts=artifacts,
        metadata_path=metadata_path,
        orig_head=orig_head,
    )

Release tools
=============

`stage-release` stages an OpenSSL release: it makes the release commits, tags
the release, and writes the tarball, checksums and a metadata file.

Nothing here signs, pushes or uploads anything.  The release tag is annotated
but **not** signed, because the signing key lives on an HSM that the build
host cannot reach — signing the tag and the tarball is a separate step, run
where that access exists.  Shipping the artifacts is the caller's job.

Requirements
------------

Python 3.10 or later, and nothing else: the tool uses only the standard
library, so it runs on release build hosts without installing anything.
`pytest` is needed to run the tests, but not to run the tool.

`--reviewer` validates names against the committer and CLA databases at
`api.openssl.org`, so that option needs network access.  Without it, nothing
here reaches the network.

Usage
-----

Run it from inside an OpenSSL **source** worktree, with the branch you are
releasing from checked out:

```sh
$TOOLS/release-tools/stage-release --reviewer=NAME
$TOOLS/release-tools/stage-release --help
$TOOLS/release-tools/stage-release --manual
```

It refuses to run unless the branch is `master` or a recognised release
branch, and unless the worktree is clean.  With no `--alpha`, `--beta` or
`--final`, the next release is worked out from the state of the branch.

Layout
------

The executable lives here; the code lives in `lib/openssl_tools/`, shared
with review-tools so the two can import each other directly.

```
release-tools/stage-release          the executable; puts lib/ on sys.path
lib/openssl_tools/stagerelease/
    cli.py               argument handling and the closing message
    stage.py             the staging run, start to finish
    state.py             the release state machine (pure function)
    version/             the two versioning schemes
        base.py          ReleaseState, and the Scheme interface
        modern.py        VERSION.dat, OpenSSL 3.0 and later
        legacy.py        opensslv.h, before OpenSSL 3.0
    fixups.py            the per-file CHANGES/NEWS/README/spec edits
    copyright_year.py    the copyright year pass
    tarball.py           tarball construction and checksums
    metadata.py          the .dat file describing a staged release
    reviewers.py         Reviewed-by: trailers, via ..reviewtools
    build.py             ./Configure and make
    git.py               the git operations a staging run needs
    run.py               running external commands
    report.py            progress output
    textutil.py          line handling and file I/O
    errors.py            ReleaseError
lib/tests/stagerelease/              pytest suite
```

`build.py`, `git.py` and `run.py` exist so that `stage.py` can be tested
without configuring or building OpenSSL, which is what made the shell version
untestable.  Inject a stub `Build` and the whole staging run -- branch
decisions, commit sequence, artifact naming -- is exercised in milliseconds;
see `lib/tests/stagerelease/test_stage.py`.

Reviewer trailers are added in-process: `reviewers.py` imports
`..reviewtools`, so `addrev` does not need to be on PATH.

Both filename conventions are handled throughout: pre-3.0 OpenSSL uses
`CHANGES`/`NEWS`, while 3.0 and later use `CHANGES.md`/`NEWS.md`.  They are
not interchangeable.

Tests
-----

```sh
cd lib
uvx pytest              # or: pytest, with pytest installed
```

The suite covers both subpackages.  It needs `git`, `make` and `gzip` on
PATH, builds throwaway repositories under the pytest tmp directory, and
touches neither the network nor any OpenSSL checkout.

Two things worth knowing when changing this code:

- `stagerelease/state.py` is a pure function of (scheme, state, method, date).  Every
  release transition is testable without a repository; keep it that way.
- The fixups in `stagerelease/fixups.py` rewrite published changelogs, so a mistake there
  is expensive.  `lib/tests/stagerelease/test_fixups.py` asserts on exact output text rather
  than on substrings, deliberately.

History
-------

This replaces `stage-release.sh`, the `release-aux/*-fn.sh` helpers and the
twelve `release-aux/fixup-*.pl` scripts.  The port was verified against the
shell it replaced across 230 combinations of version state and requested
transition.  All 216 OpenSSL 3.0+ cases matched exactly.  Fourteen pre-3.0
cases differ, and in every one the shell wrote a corrupt
`OPENSSL_VERSION_NUMBER`: its patch-letter decoder was `^(z)*(.)$`, a capture
group under `*`, which keeps only the final repetition.  That misread any
chain of more than one `z`, and failed outright on an empty patch level.
Neither was reachable in practice — 1.x is end-of-life and never went past
`zh` — and both are covered by tests now.

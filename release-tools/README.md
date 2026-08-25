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

That validation is a preflight check: it runs before the copyright pass,
before `./Configure`, and before any commit.  A reviewer who is unknown, has
no CLA or is not a committer aborts the run in well under a second, leaving
the worktree exactly as it was.

Usage
-----

Run it from inside an OpenSSL **source** worktree, with the branch you are
releasing from checked out:

```sh
$TOOLS/release-tools/stage-release --reviewer=NAME
$TOOLS/release-tools/stage-release --help
$TOOLS/release-tools/stage-release --manual
```

`stage-release` needs no `PATH` setup -- Jenkins invokes it by absolute
path.  If you do want it on `PATH`, add the directory or symlink the script;
it resolves its own real path before locating `lib/openssl_tools`.  Do not
copy it out of the checkout, because then it cannot find the package.

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
`..reviewtools`, so `addrev` does not need to be on PATH.  It resolves the
names once, up front, and then only rewrites messages -- so the five commits
a run makes cost one round trip between them, not five.

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

Linting
-------

```sh
cd lib
uvx ruff check . && uvx ruff format --check .
# the entry scripts have no .py extension, so name them explicitly:
uvx ruff check --config pyproject.toml \
    ../release-tools/stage-release ../review-tools/addrev \
    ../review-tools/gitaddrev ../review-tools/cherry-checker
```

The code is `ruff format`-ed at the 100 column limit set in
`lib/pyproject.toml`; keep it that way rather than hand-wrapping.

```sh
cd lib
uvx --with pytest mypy
```

The package is fully annotated and `disallow_untyped_defs` is on for it.
Test functions stay unannotated, but `check_untyped_defs` means their bodies
are still checked -- which is where the value is, because that is what
catches a test double drifting away from the interface it stands in for.

Every injectable seam is typed as a Protocol (`BuildSystem`, `PersonSource`,
`ListingSource`, `GitQueries`, `CommandRunner`, `UrlOpener`) rather than as
the concrete class.  That is deliberate: a parameter typed to the one real
implementation makes substitution a type error, which defeats the point.

The rule set is pinned in `lib/pyproject.toml` rather than left to ruff's
default, which changes between releases.  Two rules are switched off there
with reasons: `DTZ011`, because release dates are naive local dates by
design, and nothing else.  Individual `noqa` comments all carry a reason.

Self-contained executables
--------------------------

`lib/build-pyz` packs the shared package plus one entry point into a
zipapp, so a single file runs with nothing but a Python 3.10 interpreter --
no checkout, no PATH setup, no installed packages:

```sh
cd lib
./build-pyz                       # all four, into lib/dist/
./build-pyz addrev gitaddrev      # just these
./build-pyz -o /tmp/x -p /usr/bin/python3.11
```

Each archive is about 60 KiB and carries the whole `openssl_tools` package,
so any of them can stand alone:

```
lib/dist/stage-release
lib/dist/addrev
lib/dist/gitaddrev
lib/dist/cherry-checker
```

They are named exactly like the scripts they replace, with **no `.pyz`
suffix**, so one can be copied straight over an existing install:

```sh
cp lib/dist/addrev lib/dist/gitaddrev /usr/local/bin/
```

The suffix is unnecessary on Unix -- the kernel reads the shebang -- and
would only stop the file being a drop-in replacement.  Pass
`--extension .pyz` if you want it anyway.  Note that `file` reports these
as "Zip archive data" rather than as a script; that is what a zipapp is.

Two things worth knowing:

- **They are byte-reproducible.** Member timestamps are normalised, so
  building the same tree twice gives identical archives.  Set
  `SOURCE_DATE_EPOCH` to pin the timestamp to something other than the
  default.
- **`addrev.pyz` needs nothing beside it.** It runs gitaddrev as a
  subprocess, and inside an archive it points `PYTHONPATH` at the `.pyz`
  itself, which Python imports from happily.  Verified with
  `gitaddrev.pyz` absent.

### One archive for everything

`--multicall` builds a single busybox-style archive that decides which tool
to run from the name it was invoked as:

```sh
cd lib
./build-pyz --multicall --links
```

```
lib/dist/openssl-tools
lib/dist/addrev         -> openssl-tools
lib/dist/gitaddrev      -> openssl-tools
lib/dist/stage-release  -> openssl-tools
lib/dist/cherry-checker -> openssl-tools
```

60 KiB total instead of 240 KiB, and one file to install rather than four.
Symlinks, hardlinks and plain copies all work,
because the dispatch reads `argv[0]` rather than locating anything on disk
-- so unlike the scripts in `release-tools/` and `review-tools/`, copying
one of these out to a fixed path is fine.

It also answers to a subcommand, for when `argv[0]` is not yours to choose:

```sh
./openssl-tools addrev --nopr --reviewer=...
```

Invoked under an unrecognised name with no subcommand, it lists what it
does know.

`lib/dist/` is build output and is git-ignored.

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

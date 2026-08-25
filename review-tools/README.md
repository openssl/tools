# Review tools

Helpers for reviewing and merging OpenSSL pull requests.

## Requirements

`addrev`, `gitaddrev` and `cherry-checker` are Python and need only Python
3.10 or later — no packages, and no `OpenSSL-Query`.  They query
`api.openssl.org` directly; see
[`lib/openssl_tools/reviewtools/query.py`](../lib/openssl_tools/reviewtools/query.py).

Those three are thin entry points; the code lives in
[`lib/openssl_tools/reviewtools/`](../lib/openssl_tools/reviewtools/),
alongside the release-staging package so the two can import each other.

`ghmerge`, `opensslbuild`, `opensslpull` and `pick-to-branch` are shell;
`ghmerge` additionally needs `jq`.  `ghlink` is Perl.

`OpenSSL-Query` is still in this repository, but nothing here uses it any
more.

## Putting the scripts on PATH

`ghmerge` invokes `addrev` by bare name, and `addrev` invokes `gitaddrev`, so
at least those two need to be reachable.  Two ways work:

```sh
# add the directory
export PATH="$TOOLS/review-tools:$PATH"

# or symlink individual scripts
ln -s "$TOOLS/review-tools/addrev"    ~/bin/addrev
ln -s "$TOOLS/review-tools/gitaddrev" ~/bin/gitaddrev
```

Symlinks are fine because each script resolves its own real path before
locating the shared `lib/openssl_tools` package, so linking them into a `bin`
directory works.

**Do not copy the scripts out of the checkout.**  They find the package at
`../lib` relative to their own location, so a copy elsewhere cannot see it.
The scripts say so rather than dying with a traceback:

```
addrev: cannot import openssl_tools from /somewhere/lib: No module ...
This script has to stay inside the tools repository checkout. To
put it on PATH, add its directory or symlink the script -- do not
copy it out.
```

If a copy is genuinely needed — a container image that installs the scripts
to a fixed location, say — set `PYTHONPATH` to the `lib` directory instead:

```sh
PYTHONPATH=$TOOLS/lib addrev ...
```

## Self-contained executables

If you would rather not depend on the checkout at all, build zipapps:

```sh
cd lib
./build-pyz addrev gitaddrev cherry-checker
cp dist/addrev dist/gitaddrev /usr/local/bin/
```

Each is about 60 KiB, carries the whole package, and runs with only a Python
3.10 interpreter.  They are named exactly like the scripts they replace — no
`.pyz` suffix — so they drop straight over an existing install.  The archived
`addrev` does not need the archived `gitaddrev` beside it: it points
`PYTHONPATH` at its own archive when spawning the message filter.

Or one busybox-style archive for all of them, symlinked to each name:

```sh
cd lib
./build-pyz --multicall --links
```

Symlinks, hardlinks and copies all work there, since the dispatch reads
`argv[0]`.  `openssl-tools addrev ...` works too.

See [`release-tools/README.md`](../release-tools/README.md) for the full
description.

## Tests

```sh
cd lib
uvx pytest          # or: pytest, with pytest installed
```

## Environment

Some of the scripts use the REST API at <https://api.openssl.org>, and
`ghmerge` also uses <https://api.github.com>.  The `https_proxy` and
`no_proxy` environment variables are honoured.

## The scripts

### addrev

`addrev` and `gitaddrev` are a pair that add or edit reviewers on commits:
`gitaddrev` is a `git filter-branch --msg-filter`, and `addrev` drives it
over a commit range.

To use them, put both on your `PATH`.  release-tools calls the same code
in-process, so staging a release does not need them on `PATH`.

Run `addrev --help` for usage, and `addrev --list` for the known reviewer
names.

A reviewer already named in the message is not added again.  If the
committer is not the author of the commit, they are added automatically.

Reviewer names may be given as known lower-case short names, as GitHub IDs
prefixed with `@`, or as known email addresses with `--reviewer`.

Every named reviewer must be a known person, must have a CLA on file, and
must be a committer — a member of the `commit` group, which is the same set
`addrev --list` prints.  Naming anyone else fails the run and says who.

The commit's author is held to a laxer standard: authors never get a
`Reviewed-by:` trailer, and an outside contributor's patch still has to be
mergeable, so a non-committer author simply does not count towards the
reviewer total.

The tool reads databases on `api.openssl.org`, so it needs network access.
The transfer may take many seconds, particularly with `--list`.

Examples:

```sh
addrev --prnum=1234 steve
addrev 1234 -2 steve
addrev 1234 -2 steve @richsalz
addrev 1234 -2 --reviewer=steve --reviewer=rsalz@openssl.org
```

### cherry-checker

Lists the commits in the symmetric difference of two branches, marking which
ones already have an equivalent on the other side, so you can see what is
still eligible for cherry-picking.

```sh
cherry-checker                       # master vs the highest local openssl-N.M
cherry-checker master openssl-3.5    # or name both explicitly
cherry-checker -a                    # include commits already picked
cherry-checker -s                    # sort by PR number and date
cherry-checker -r                    # compare the remote branches
```

### ghmerge

`ghmerge` calls `addrev` and pushes reviewed and approved GitHub pull
requests.  It includes several safety precautions: it shows the diff, shows
the resulting commit messages, and by default rebuilds everything.

It works on the current branch, which should be `master` or one of the stable
release branches.  The default remote is the first one whose push URL matches
the canonical repositories, so a typical session starts:

```sh
git remote -v
git fetch origin
git checkout master
```

Usage patterns:

```sh
ghmerge <prnum> <reviewer>...
ghmerge --tools --squash <prnum> <reviewer>...
```

The default commit post-processing is `git rebase -i --autosquash`.  Options:

| Option | Effect |
| --- | --- |
| `--noautosquash` | interactive post-processing without `--autosquash` |
| `--squash` | non-interactive `git merge --ff-only --squash` |
| `--nobuild` | skip `opensslbuild`; otherwise `$CC` defaults to `ccache gcc` |
| `--remote <remote>` | the git remote to pull from and push to |
| `--target <branch>`, `--ref <branch>` | the merge target, rather than the current branch |
| `--cherry-pick [n]` | cherry-pick the last *n* commits instead of rebasing |
| `--tools`, `--installer`, `--perftools`, `--fuzz-corpora`, `--security` | target a sibling repository rather than `openssl` |

`<prnum>` is the GitHub PR number; the remaining arguments are reviewer
names, passed through to `addrev`.

### pick-to-branch

Cherry-picks a commit, or several, onto a release branch named by a short
form — `30`, `31`, or `m` for master.  If the target is not the current
branch, the current branch and its state are preserved.

```sh
pick-to-branch HEAD 31
pick-to-branch <commit> 30 2
```

### opensslbuild and opensslpull

`opensslbuild` configures, builds and runs the test suite from the top of an
OpenSSL checkout; `ghmerge` invokes it unless `--nobuild` is given.
`opensslpull` fetches and rebases the release branches and any local
branches, skipping anything listed in `.skiplist`.

### ghlink

Converts repository locations — a path, optionally with a revision and a line
number — into GitHub links.  Run `ghlink --man` for the manual.

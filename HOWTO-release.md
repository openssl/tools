# HOW TO MAKE AN OPENSSL RELEASE

This is the whole release process, from freezing the source repository to
checking the website afterwards.  It replaces the earlier
`HOWTO-make-a-release.md`, `HOWTO-stage-a-release.md` and
`HOWTO-publish-a-release.md`, which described a manual procedure that has
since been automated.

Please fix any errors you find while doing, or just after, your next release.

**A note on names.**  This document deliberately does not name internal
hosts.  Infrastructure is referred to by role — "the release pipeline", "the
signing agent", "the internal Git host" — because the pipelines already know
the addresses and an operator following this document does not need them.

## Table of contents

- [How releases actually happen](#how-releases-actually-happen)
- [Prerequisites](#prerequisites)
- [Before the release](#before-the-release)
- [Running the release](#running-the-release)
- [Signing](#signing)
- [After the pipeline](#after-the-pipeline)
- [Security releases](#security-releases)
- [Post-release tasks](#post-release-tasks)
- [Doing it by hand](#doing-it-by-hand)
- [Known failure modes](#known-failure-modes)

## How releases actually happen

Releases are made by CI pipelines, not by hand.  There are three, one per
release type:

| Release type | Source | Pipeline |
| --- | --- | --- |
| Public | `openssl/openssl` on the internal Git host | `make-release` |
| Security | `openssl/security` (private, embargoed) | `make-security-release` |
| Extended | `openssl/extended-releases` | `make-extended-release` |

Every pipeline follows the same shape:

1. Check out this `tools` repository alongside the target source repository.
2. Run `release-tools/stage-release` inside the source worktree.  This makes
   the release commits, an annotated tag, the tarball and its checksums.
3. Resolve the tag and version once, and derive the staging branch names.
4. Push staging branches and open a pull request.
5. Poll until the PR has **two approving reviews**.
6. Sign the tag and the tarball on the signing agent, which is the only
   machine with HSM access.
7. Push the release branches and the signed tag to the source repository.
8. Trigger the mirror job that syncs the internal repository to the public
   one.
9. Create a **draft** GitHub release with the signed artifacts attached.

Two parameters matter on every pipeline:

- `dry_run` — turns the pushes into `git push --dry-run`.  Note this does
  **not** exercise the server-side pre-receive hooks, because no pack is
  sent.  A green dry run does not prove a real push will be accepted.
- `CHECKOUT_ONLY` — used by the job-seeding mechanism.  Leave it alone.

## Prerequisites

To run a release you need:

- Permission to run the release pipelines.
- Push access to the relevant source repository.
- Access to `openssl/release-metadata`, for advisories and release data.
- For security releases, access to the embargoed security repository.

You do **not** need a copy of the release signing key.  It lives in an HSM
and is only reachable from the signing agent; nothing you run locally signs
release artifacts.

To reproduce a release locally, or to run the manual fallback, you need
Python 3.10 or later and nothing else.

## Before the release

### Confirm the schedule

Release dates, end-of-life dates and LTS flags live in `data.json` in the
`release-metadata` repository.  Check the release you are about to make is
the one that is scheduled.

### Freeze the source repository

Three business days before the release, freeze the source repository.  The
freeze is infrastructure-as-code: set the `openssl_repo_releaser` value in
the Pulumi stack configuration for the internal Git host, in the `infra`
repository, to the release operator's login, then apply the stack.

Setting it to a non-empty value does three things at once:

- grants that person the custom **Releaser** repository role,
- enables the **Branch freeze** ruleset over every ref except
  `refs/heads/feature/*`, blocking creation, deletion, updates,
  non-fast-forward pushes and non-linear history,
- enables the **Tag freeze** ruleset over every tag.

The Releaser role is a bypass actor on both rulesets, so the named operator
can still push while everyone else is locked out.

The login is the one declared for that person in the infra repository's
people definitions, which is **not** necessarily their github.com handle —
`tomas`, not `t8m`.  A login that is not an organisation member is rejected
when the stack is applied, with a message telling you so.

### Notify the committers

Mail the committers list to say the tree is frozen and how long the freeze
is expected to last.

### Make sure the source is ready

For security releases, merge all applicable and approved security PRs first.

Check that `CHANGES.md` and `NEWS.md` have been updated and reviewed.
`NEWS.md` should summarise the changes; for a security release that is
usually just the list of CVEs.  Also update `NEWS.md` on `master` to mention
the release — bullet points only, leave the date as **under development**.

> Before OpenSSL 3.0 these files are called `CHANGES` and `NEWS`.  The
> tooling handles both, and they are not interchangeable.

## Running the release

Run the pipeline for the release type you are making.  The parameters are
the release branch, the reviewers, and whether this is an alpha, beta or
final release.

The pipeline will stop and wait at the review gate.  Two approvals are
required, and the pipeline polls for them; it does not proceed on one.

### What `stage-release` does

Run from inside a source worktree, on a clean tree, on `master` or a
recognised release branch.  In order:

1. Validates the reviewers against the committer and CLA databases.  This is
   a **preflight** check — an unknown reviewer, one without a CLA, or one who
   is not a committer aborts the run in under a second, before anything is
   written or built.
2. Updates copyright years and commits, if anything changed.
3. Runs `./Configure` and `make update`, plus symbol renumbering and FIPS
   checksums where the branch has those targets, and commits.
4. Writes the release version, applies the per-file `CHANGES`/`NEWS`/`README`
   edits, commits, and creates an **annotated, unsigned** tag.
5. Builds the tarball and writes `.sha1` and `.sha256` beside it.
6. Writes `openssl-<version>.dat` describing what was staged.
7. Returns the branch to development with a post-release commit, and — when
   releasing from `master` at patch 0 — creates the new release branch and
   moves `master` on to the next minor version.

It signs nothing, pushes nothing and uploads nothing.  It does not generate
announcement text; that was removed.

Run `release-tools/stage-release --manual` for the full description.

## Signing

Release artifacts are OpenPGP-signed with a key held in a hardware security
module.  Signing happens in a dedicated pipeline stage pinned to the one
agent with HSM access; the tree crosses agents as a stash, and only the
signed tag object and the detached signature come back.

The certificate is two-tier: a Certify-only primary key protected by an
operator card quorum, and a module-protected signing subkey used unattended.
**Release artifacts and release tags are signed with the subkey, never the
primary.**

The published certificate is fetched fresh from WKD for
`openssl@openssl.org` at signing time rather than being kept in a keystore.
The current certificate fingerprint is
`B146647E45A7B33947AB226B2A2C87D161692D40`, signing subkey key ID
`64ED7B1DCCE71CB2`.

The release key used before 2026 —
`BA5473A2B0587B07FB27CF2D216094DFD0CB81EF` — is retired and is no longer
used by any pipeline.

Two couplings worth knowing:

- A release tag is rejected by the `check-tags` pre-receive hook unless the
  signing certificate is in that hook's allowlist.  When the release
  certificate is rotated, the hook repository must be updated in the same
  breath.
- The hook verifies with GnuPG and only cares *which* key signed.  Tags
  signed through Sequoia are ordinary v4 RSA signatures that GnuPG verifies
  fine, so there is no tool incompatibility to work around.

The key lifecycle itself — generating the primary and subkey, issuing and
rotating the certificate, issuing revocation certificates — is documented
separately in [`openpgp-tools/README.md`](openpgp-tools/README.md), which is
also where the module-specific details live.

## After the pipeline

### Publish the GitHub release

The pipeline leaves a **draft** release with the signed tarball, its `.asc`
signature and its checksums attached.  Check that:

- the tarball length and the checksums match,
- the signature verifies against the published certificate,
- alpha and beta releases are marked as a pre-release,
- the newest release is marked as the latest release.

Then publish it.  The release notes are pulled automatically from the
release-metadata news endpoint.

### Update the release metadata

In the `release-metadata` repository:

- Update `data.json` if the schedule, EOL or LTS status changed.
- For a security release, add the advisory to `secadv/` and the
  machine-readable record to `secjson/`.

Open a pull request, get it reviewed, and merge it.

> `newsflash.md` in that repository is historical and no longer drives
> anything.  Do not add to it.

### Check the website

The website renders the release table, the release notes and the advisories
from `release-metadata`, and deploys on merge.  Give it a few minutes, then
check:

- the source download page lists the new release,
- the news log shows it,
- the per-branch release notes pages are updated.

If something is missing, check whether the site build has run before
assuming the data is wrong.

## Security releases

In addition to everything above:

### Send the advisory

Sign the advisory as yourself and send it, from your own address, to the
public project, users and announce lists.  Send it separately to
`oss-security@lists.openwall.com` rather than cross-posting.

Check the list archives to confirm the messages arrived.

### Register the CVEs

Inform MITRE about any CVE in the release; the procedure is at the top of
`cvepool.txt` in the security repository.

Close the GitHub advisory without publishing it there, and delete the
private fork if one was created.

## Post-release tasks

### Unfreeze the source repository

Clear the `openssl_repo_releaser` value in the Pulumi stack configuration —
set it to the empty string or remove it — and apply the stack.  That removes
the Releaser collaborator and disables both freeze rulesets.

### Update the provider compatibility tests

For a new minor release, add the new tag to
`.github/workflows/provider-compatibility.yml` in the source repository —
for the released version **and every later branch**.

### Keep in touch

Watch the mailing lists for the next few hours.  Fix what comes up, and in
the worst case make another release.

## Doing it by hand

The manual path exists for when automation fails or for a release the
pipelines are not set up for.  It is the same tool, run directly:

    git clone <tools-repo> tools          # referred to below as $TOOLS
    git clone <source-repo> openssl
    cd openssl
    git checkout <release-branch>
    $TOOLS/release-tools/stage-release --reviewer=NAME --reviewer=NAME

Staging several releases from one repository is easiest with worktrees:

    git worktree add ../openssl-3.5 openssl-3.5

Then check the result before pushing anything: read the commits it made,
read the `.dat` file, and confirm the tag points at the release commit.  The
tag is unsigned at this point and must be signed on the signing agent before
it is pushed, because the pre-receive hook rejects unsigned release tags.

**Do not push** until the review and signing steps have happened.

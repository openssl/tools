# HOW TO STAGE A RELEASE

This file documents how to make an OpenSSL release.  Please fix any errors
you find while doing, or just after, your next release!

Anyone with access to the necessary resources may stage a release.  Reviews
for doing so isn't necessary, that's done "naturally" as part of publishing,
see [HOWTO-publish-a-release.md](HOWTO-publish-a-release.md).

# Automation

**Staging releases is becoming automated**, so this document will soon only
be interesting to know how to perform this manually, should the need arise
(automation failure, or to stage releases that automation isn't prepared
for).

This automation is currently still undergoing tests, and isn't quite
reflected in [HOWTO-publish-a-release.md](HOWTO-publish-a-release.md).
Updates pending!

# Table of contents

-   [Prerequisites](#prerequisites)
    -   [Software](#software)
    -   [Repositories](#repositories)
    -   [PGP / GnuPG key](#pgp-gnupg-key)
    -   [SFTP access](#check-your-access)
    -   [Prepare your repository checkouts](#prepare-your-repository-checkouts)
-   [Staging tasks](#staging-tasks)

    -   [Generate the tarball and announcement text](#generating-the-tarball-and-announcement-text)
    -   [Remember the results](#remember-the-results)

# Prerequisites

## Software

Apart from the basic operating system utilities, you must have the following
programs in you `$PATH`:

- openssl
- gpg
- git
- ssh
- sftp

(note: this may not be a complete list)

## Repositories

You must have access to the following repositories:

-   `git@github.openssl.org:otc/tools.git`

    This contains the release staging tool.

-   Any of:

    -   `git@github.openssl.org:openssl/openssl.git`

        This is the public source repository, so is only necessary to stage
        a public release, which are those that haven't reached End-Of-Life
        yet.

    -   `git@github.com:openssl/security.git`

        This is the security source repository, where security fixes are
        staged before being publically released.  It is used as source
        repository instead of `openssl/openssl` to stage a security
        release.

    -   `git@github.openssl.org:openssl/premium.git`

        This is the source repository for premium customers, used for both
        security and non-security releases.

## PGP / GnuPG key

You must have OpenSSL's team key:

    $ gpg --list-secret-key BA5473A2B0587B07FB27CF2D216094DFD0CB81EF
    sec   rsa4096 2024-04-08 [SC] [expires: 2026-04-08]
          BA5473A2B0587B07FB27CF2D216094DFD0CB81EF
    uid           [ultimate] OpenSSL <openssl@openssl.org>

If you don't have it and think you should, get an export from someone on the
team that has it.

## SFTP access

To stage a release, you must have appropriate access to OpenSSL's upload
address, `upload@dev.openssl.org`.  To test this, try to log in with sftp:

    sftp upload@dev.openssl.org

## Prepare your repository checkouts

-   To stage a release, you need to checkout the release staging tool

        git clone git@github.openssl.org:otc/tools.git tools

    The resulting directory will be referred to as `$TOOLS`

-   For each release to be staged, you need to checkout its source
    repository, which is one of:

    -   `git clone git@github.openssl.org:openssl/openssl.git`
    -   `git clone git@github.com:openssl/security.git`
    -   `git clone git@github.openssl.org:openssl/premium.git`

-   If you're staging multiple releases from one repository in one go, there
    are many ways to deal with it.  One possibility, available since git 2.5,
    is to use `git worktree`:

        (cd openssl;
         git worktree add ../openssl-1.1.1 OpenSSL_1_1_1-stable)

# Staging tasks

## Generate the tarball and announcement text

*The changes in this section should be made in your clone of the openssl
source repo*

To generate and stage a release tarball and announcement text, there is a
script `$TOOLS/release-tools/stage-release.sh`.  It's expected to be run
while standing in the worktree of an OpenSSL source repository, and the
expects the checked out branch to be the branch to stage the release from,
matching one of OpenSSL release branch patterns.

The stage-release script has a multitude of other options that are useful
for specific cases, and is also self-documented:

-   To get a quick usage reminder:

        $TOOLS/release-tools/stage-release.sh --help

-   To get a man-page:

        $TOOLS/release-tools/stage-release.sh --manual

It is generally called like this:

    $TOOLS/release-tools/stage-release.sh --reviewer=NAME \
        --local-user=BA5473A2B0587B07FB27CF2D216094DFD0CB81EF

This scripts will perform a number of preparatory tasks, such as updating
the copyright year, running `make update`, update release dates, and move
the branch to the next development version.  This results not only in a
staged release tarball and announcement text, but also in a set of commits.

After having run the stage-release script, verify that its results are
sensible.  Check the commits that were added, using for example `git log`.
Check the signed announcement .asc file.  Check that the tarball length and
hashes match in the .md5, .sha1, .sha256, and review the announcment file.
Check the data left in the metadata .dat file.

*Do not push* the local commits to the source repo at this stage.

## Remember the results

*Make sure to take note of all the instructions the stage-release script gave
you at the end.  They will be needed when
[publishing the release](HOWTO-publish-a-release.md).*

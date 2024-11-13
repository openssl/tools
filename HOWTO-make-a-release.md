# HOW TO MAKE A RELEASE

This file documents the overall OpenSSL release process.  Some parts of this
process is documented in other files that go into deeper detail.

# Table of contents

-   [Prerequisites](#prerequisites)
    -   [Software](#software)
    -   [Repositories](#repositories)
    -   [A method for reviewing](#a-method-for-reviewing)
-   [Preparation tasks](#preparation-tasks)
    -   [Freeze the source repository](#freeze-the-source-repository) [three business days before release]
    -   [Make sure that the openssl source is up to date](#make-sure-that-the-openssl-source-is-up-to-date)
-   [Stage the release](#stage-the-release)
-   [Publish the release](#publish-the-release)
-   [Post-releasing tasks](#post-publishing-tasks)
    -   [Unfreeze the source repository](#unfreeze-the-source-repository)
    -   [Update compatibility tests](#update-the-provider-backwards-compatibility-tests)
    -   [Keep in touch](#keep-in-touch)


# Prerequisites

## Software

Apart from the basic operating system utilities, you must have the following
programs in you `$PATH`:

- ssh
- git

(note: this may not be a complete list)

## Repositories

You must have access to the following repositories:

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

## A method for reviewing

In some parts of the release process, peer review may apply.  The review
methods are specified in more detail in those parts.

# Preparation tasks

Some of the actions in this section need to be repeated for each OpenSSL
version released.

## Prepare your repository checkouts

-   For each release to be staged, you need to checkout its source
    repository, which is one of:

    -   `git clone git@github.openssl.org:openssl/openssl.git`
    -   `git clone git@github.com:openssl/security.git`
    -   `git clone git@github.openssl.org:openssl/premium.git`

## Freeze the source repository

Three business day before the release, freeze the appropriate source
repository.

This locks out everyone but the named user, who is doing the release, from
doing any pushes.  Someone other than the person doing the release should
run the command.

This must be done from a checkout of that source repository, so for public
as well as security releases:

    git push git@github.openssl.org:openssl/openssl.git HEAD:refs/frozen/NAME

and for premium releases:

    git push git@github.openssl.org:openssl/premium.git HEAD:refs/frozen/NAME

Where `NAME` is the github username of the user doing the release.

Note: it currently doesn't matter what source branch is used when pushing,
the whole repository is frozen either way.  The example above uses whatever
branch you happen to have checked out.

Note: `git@github.openssl.org:openssl/security.git` is derived from
`git@github.openssl.org:openssl/openssl.git`, so when freezing the latter,
it's implied that the former is frozen as well.

## Notify comitters and platform owners of the freeze

When the tree is frozen, an email should be sent to openssl-comitters@openssl.org, as well as to the community platform owners (documented [here](https://www.openssl.org/policies/general-supplemental/platforms.html))indicating that the tree is frozen, and how long the freeze is expected to last.  It should also indicate to the community platform owners that additional, more frequent testing during the freeze would be appreciated, as community platforms are not all in our CI system.  This will help mitigate inadvertent breakage during the freeze period on platforms we do not consistently test against.


## Make sure that the openssl source is up to date

For security releases, merge all applicable and approved security PRs.

*NOTE: the files CHANGES.md and NEWS.md are called CHANGES and NEWS in
OpenSSL versions before version 3.0*

For each source checkout, make sure that the CHANGES.md and NEWS.md files
have been updated and reviewed.

The NEWS file should contain a summary of any changes for the release;
for a security release, it's often simply a list of the CVEs addressed.
You should also update NEWS.md in the master branch to include details of
all releases.  Only update the bullet points - do not change the release
date, keep it as **under development**.

# Stage the release

See [HOWTO-stage-a-release.md](HOWTO-stage-a-release.md), which describes
this in detail.

This may be done independently of [publishing the release](#publish-the-release).
However, if done manually, the same person should stage and publish the
release, as doing it this way depends on that person's local clones and
checkouts.

# Publish the release

See [HOWTO-publish-a-release.md](HOWTO-publish-a-release.md), which
describes this in detail.

This may be done independently of [staging the release](#stage-the-release).
However, if done manually, the same person should stage and publish the
release, as doing it this way depends on that person's local clones and
checkouts.

# Post-releasing tasks

## Unfreeze the source repository.

This must be done from a checkout of the appropriate source repo:

    git push --delete git@github.openssl.org:openssl/openssl.git \
        refs/frozen/NAME

or:

    git push --delete git@github.openssl.org:openssl/premium.git \
        refs/frozen/NAME

## Update the provider backwards compatibility tests

In the case of a new minor release, the tags being tested by the
`.github/workflows/provider-compatibility.yml`
script need to be updated for the released version and **all** subsequent (i.e.
higher numbered versions) to include the tag for this release.

## Keep in touch

Check mailing lists over the next few hours for reports of any success or
failure.  If necessary fix these and in the worst case make another
release.

# HOW TO MAKE A RELEASE

This file documents how to make an OpenSSL release.  Please fix any errors
you find while doing, or just after, your next release!

Releases are done by one person, with a second person acting as the reviewer
and additional tester.

# Table of contents

-   [Prerequisites](#prerequisites)
    -   [Software](#software)
    -   [Repositories](#repositories)
    -   [PGP / GnuPG key](#pgp-gnupg-key)
    -   [SSH access](#check-your-access)
    -   [A method for reviewing](#a-way-to-reviewing)
-   [Pre-publishing tasks](#pre-publishing-tasks)
    -   [Freeze the source repository](#freeze-the-source-repository) [the day before release]
    -   [Prepare your repository checkouts](#prepare-your-repository-checkouts)
    -   [Make sure that the openssl source is up to date](#make-sure-that-the-openssl-source-is-up-to-date)
    -   [Generate the tarball and announcement text](#generating-the-tarball-and-announcement-text)
        -   [OpenSSL 3.0 and on](#openssl-3.0-and-on)
        -   [OpenSSL before 3.0](#openssl-before-3.0)
    -   [Update the website locally](#update-the-website-locally) [do not push]
-   [Publish the release](#publish-the-release)
-   [Post-publishing tasks](#post-publishing-tasks)
    -   [Check the website](#check-the-website)
    -   [Send the announcement mail](#send-the-announcement-mail)
    -   [Send out the Security Advisory](#send-out-the-security-advisory)
    -   [Unfreeze the source repository](#unfreeze-the-source-repository)
    -   [Security fixes](#security-fixes)
    -   [Keep in touch](#keep-in-touch)


# Prerequisites

## Software

Apart from the basic operating system utilities, you must have the following
programs in you `$PATH`:

- openssl
- ssh
- gpg
- git

(note: this may not be a complete list)

## Repositories

You must have access to the following repositories:

-   `openssl-git@git.openssl.org:openssl.git`

    This is the usual main source repository

-   `openssl-git@git.openssl.org:openssl-web.git`

    This is the website repository

-   `openssl-git@git.openssl.org:tools.git`

    This contains certain common tools

## PGP / GnuPG key

You must have a PGP / GnuPG key, and its fingerprint should be present in
the file `doc/fingerprints.txt` in the source of the immediately prior
OpenSSL release.

## SSH access

To perform a release, you must have appropriate access to OpenSSL's
development host, dev.openssl.org.  To test this, try to log in with ssh:

    ssh dev.openssl.org

You must also check that you can perform tasks as the user 'openssl' on
dev.openssl.org.  When you have successfully logged in, test your access to
that user with sudo:

    sudo -u openssl id

## A method for reviewing

For reviewing to take place, the release person and the reviewer need a way
to share changes that are being applied.  Most commonly, that's done as PRs
(for normal releases) or security advisories (for undisclosed security
fixes) through Github.

Security advisories are created using the Github Security tab, and will
generate a private repository, to which you can add collaborators (the
reviewer, for instance), and use it to fix the issue via pull requests.
For more information, please read Github's [creating a security advisory],
including the "Next Steps" at the end of that page.

[creating a security advisory]:
<https://docs.github.com/en/free-pro-team@latest/github/managing-security-vulnerabilities/creating-a-security-advisory>

The release person and the reviewer are allowed to use other means to share
the commits to be reviewed if they desire.

The release person and the reviewer must have a conversation to confirm or
figure out how the review shall be done.

# Pre-publishing tasks

Some of the actions in this section need to be repeated for each OpenSSL
version released.

## Freeze the source repository

The day before the release, freeze the main repository.  This locks out
everyone but the named user, who is doing the release, from doing any
pushes.  Someone other than the person doing the release should run the
command.  For example:

    ssh openssl-git@git.openssl.org freeze openssl NAME

## Prepare your repository checkouts

You will need to checkout at least three working trees:

-   one for the website

        git clone openssl-git@git.openssl.org:openssl-web.git website

-   one for extra tools

        git clone openssl-git@git.openssl.org:tools.git tools

    The resulting directory will be referred to as `$TOOLS`

-   At least one for openssl source

        git clone openssl-git@git.openssl.org:openssl.git

    If you're doing multiple releases in one go, there are many ways to deal
    with it.  One possibility, available since git 2.5, is to use `git
    worktree`:

        (cd openssl;
         git worktree add ../openssl-1.1.1 OpenSSL_1_1_1-stable)

## Make sure that the openssl source is up to date

The person doing the release and the reviewer should both sanity-check the
source to be released at this point.  Checks to consider include building
and verifying that make test passes on multiple plaforms - Linux, Windows,
etc.

*NOTE: the files CHANGES and NEWS are called CHANGES.md and NEWS.md in
OpenSSL versions from version 3.0 and on*

For each source checkout, make sure that the CHANGES and NEWS files have
been updated and reviewed.

The NEWS file should contain a summary of any changes for the release;
for a security release, it's often simply a list of the CVEs addressed.
You should also update NEWS.md in the master branch to include details of
all releases.  Only update the bullet points - do not change the release
date, keep it as **under development**.

Add any security fixes to the tree and commit them.

Make sure that the copyrights are updated.  This script will update the
copyright markers and commit the changes (where $TOOLS stands for the
openssl-tools.git checkout directory):

    $TOOLS/release-tools/do-copyright-year

Obtain approval for these commits from the reviewer and add the reviewed-by
headers as required.

*Do* send the auto-generated commits to the reviewer and await their
approval.

*Do not push* changes to the main source repo at this stage.
(the main source repo being `openssl-git@git.openssl.org:openssl.git`)

## Generate the tarball and announcement text

*The changes in this section should be made in your clone of the openssl
source repo*

The method to generate a release tarball and announcement text has changed
with OpenSSL 3.0, so while we continue to make pre-3.0 OpenSSL releases,
there are two methods to be aware of.

Both methods will leave a handful of files, most importantly the release
tarball.  When they are done, they display a set of instructions on how to
perform the publishing tasks, *please take note of them*.

After having run the release script, verify that its results are sensible.
Check the commits that were added, using for example `git log`.  Check the
signed announcement .asc file.  Check that the tarball length and hashes
match in the .md5, .sha1, .sha256, and review the announcment file.

*Do* send the auto-generated commits to the reviewer and await their
approval.

*Do not push* changes to the main source repo at this stage.
(the main source repo being `openssl-git@git.openssl.org:openssl.git`)

### OpenSSL 3.0 and on

The release generating script is in the OpenSSL source checkout, and is
generally called like this:

    dev/release.sh --reviewer=NAME

This script has a multitude of other options that are useful for specific
cases, and is also self-documented:

-   To get a quick usage reminder:

        dev/release.sh --help

-   To get a man-page:

        dev/release.sh --manual

### OpenSSL before 3.0

The release generating script is in the tools checkout, represented here
with $TOOLS, and is generally called like this:

    $TOOLS/release-tools/mkrelease.pl --reviewer=NAME

The manual for that script is found in `$TOOLS/release-tools/MKRELEASE.md`

## Update the website locally

*The changes in this section should be made in your clone of the openssl
web repo*

Update the news/newsflash.txt file.  This normally is one or two lines.
Just copy and paste existing announcements making minor changes for the date
and version number as necessary.  If there is an advisory then ensure you
include a link to it.

Update the news/vulnerabilities.xml file if appropriate.

If there is a Security Advisory then copy it into the news/secadv directory.

*Do* send the commits to the reviewer and await their approval.

Commit your changes, but *do not push* them to the website repo at this stage.
(the website repo being `openssl-git@git.openssl.org:openssl-web.git`)

# Publish the release

*BE CAREFUL*  This section makes everything visible and is therefore largely
irreversible.  If you are performing a dry run then DO NOT perform any steps
in this section.

Check that the release has been uploaded properly.  The release tarballs and
associated files should be in ~openssl/dist/new.  They should be owned by
the openssl userid and world-readable.

Copy the tarballs to appropriate directories.  This can be done using the
do-release.pl script.  See $TOOLS/release-tools/DO-RELEASE.md for a
description of the options.  For example:

    sudo -u openssl perl ~openssl/do-release.pl --copy --move

This will copy the relevant files to the website and move them from
`~openssl/dist/new` to `~openssl/dist/old` so they will not seen by a
subsequent release.  Alternatively if you want to perform one release at a
time or copy/move the files manually, see below.

The do-release.pl script will display the commands you will need to issue to
send the announcement emails later.  Keep a note of those commands for
future reference.

Verify that the tarballs are available via FTP:

    ftp://ftp.openssl.org/source/

And that they are ready for the website:

    ls /var/www/openssl/source

*For OpenSSL 3.0 and on*, push your local changes to the main source repo as
instructed by `dev/release.sh`.  You may want to sanity check the pushes by
inserting the `-n` (dry-run) option.

*For OpenSSL before 3.0*, simply push your local changes to the main source
repo, and please do remember to push the release tags as well. You may want to
sanity check the pushes by inserting the `-n` (dry-run) option. You must specify
the repository / remote and tag to be pushed:

    git push <repository> <tagname>

## Updating the website

Push the website changes you made earlier to the OpenSSL website repo.  When
you do this, the website will get updated and a script to flush the Akamai
CDN cache will be run.  You can look at things on www-origin.openssl.org;
the CDN-hosted www.openssl.org should only be a few minutes delayed.

# Post-publishing tasks

## Check the website

Verify that the release notes, which are built from the CHANGES.md file
in the release, have been updated.  This is done automatically by the
commit-hook, but if you see a problem, try the following steps on
`dev.openssl.org`:

    cd /var/www/openssl
    sudo -u openssl -H make relupd
    sudo -u openssl -H ./bin/purge-one-hour

Wait for a while for the Akamai flush to work (normally within a few minutes).
Have a look at the website and news announcement at:

-   <https://www.openssl.org/>
-   <https://www.openssl.org/news/>

Check the download page has updated properly:

-   <https://www.openssl.org/source/>

Check the notes look sensible at:

-   <https://www.openssl.org/news/newslog.html>

Also check the notes here:

-   <https://www.openssl.org/news/openssl-1.0.2-notes.html>
-   <https://www.openssl.org/news/openssl-1.1.0-notes.html>
-   <https://www.openssl.org/news/openssl-1.1.1-notes.html>

## Send the announcement mail

Send out the announcements.  Generic release announcement messages will be
created automatically by the build script and the commands you need to use
to send them were displayed when you executed do-release.pl above.
These are sent to openssl-users, openssl-project, and openssl-announce. They
should be sent from the account of the person that owns the key used for signing
the release announcement. Ensure that mutt is configured correctly - send a test
email first if necessary.

If do-release.pl was used with `--move` be sure to move the announcement
text files away from the staging directory after they have been sent.  This
is done as follows (with VERSION replaced with the version of OpenSSL to
announce):

    REPLYTO="openssl@openssl.org" mutt -s "OpenSSL version VERSION published" \
            openssl-project openssl-users openssl-announce \
            < /home/openssl/dist/new/openssl-VERSION.txt.asc
    sudo -u openssl \
        mv ~openssl/dist/new/openssl-VERSION.txt.asc ~openssl/dist/old

## Send out the Security Advisory

*The secadv file mentioned in this section is the Security Advisory
that you copied into the web repo, up in the section
[Update the website locally](#update-the-website-locally)*
 
*This section is only applicable if this is a security release*

Start with signing the Security Advisory as yourself:

    gpg --clearsign secadv_FILENAME.txt

Then copy the result to the temporary directory on dev.openssl.org:

    scp secadv_FILENAME.txt.asc dev.openssl.org:/tmp

To finish, log in on dev.openssl.org and send the signed Security
Advisory by email as the user that signed the advisory, and then remove it:

    REPLYTO="openssl@openssl.org" mutt -s "OpenSSL Security Advisory" \
            openssl-project openssl-users openssl-announce \
            </tmp/secadv_FILENAME.txt.asc
    rm /tmp/secadv_FILENAME.txt.asc

Approve the openssl-announce email.  Go to
<https://mta.openssl.org/mailman/admindb/openssl-announce>
and approve the messages.

Check the mailing list messages have arrived.

## Unfreeze the source repository.

    ssh openssl-git@git.openssl.org unfreeze openssl

## Security fixes

If this release includes security fixes with a CVE then you should inform
MITRE about them.  See the instructions at the top of cvepool.txt in omc.

Close the github advisory without pushing to github and remove the private
github fork if there was one.

## Keep in touch

Check mailing lists over the next few hours for reports of any success or
failure.  If necessary fix these and in the worst case make another
release.


# HOW TO PUBLISH A RELEASE

This file documents how to publish an OpenSSL release.  Please fix any errors
you find while doing, or just after, your next release!

Releases are staged by another procedure, separate from this.

# Table of contents

-   [Prerequisites](#prerequisites)
    -   [Software](#software)
    -   [Repositories](#repositories)
    -   [SSH access](#check-your-access)
-   [Publish the release](#publish-the-release)
    -   [Update the source repositories](#update-the-source-repositories)
    -   [Upload release files to OpenSSL downloads](#upload-release-files-to-openssl-downloads) [only public releases]
    -   [Upload release files to Github](#upload-release-files-to-github)
        -   [Web method](#web-method)
        -   [GH CLI method](#gh-cli-method)
    -   [Update the release metadata](#update-the-release-metadata)
-   [Post-publishing tasks](#post-publishing-tasks)
    -   [Check automations](#check-automations)
    -   [Check the website](#check-the-website)
    -   [Send the announcement mail](#send-the-announcement-mail)
    -   [Send out the Security Advisory](#send-out-the-security-advisory)
    -   [MITRE / CVE.org](#mitre-cve-org)

# Prerequisites

## Software

Apart from the basic operating system utilities, you must have the following
programs in you `$PATH`:

- ssh
- git

(note: this may not be a complete list)

## Repositories

You must have access to the following repositories:

-   `git@github.com:openssl/release-metadata.git`

    This contains files to be updated as part of any release.

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

## SSH access

To perform a release, you must have appropriate access to OpenSSL's
development host, dev.openssl.org.  To test this, try to log in with ssh:

    ssh dev.openssl.org

You must also check that you can perform tasks as the user 'openssl' on
dev.openssl.org.  When you have successfully logged in, test your access to
that user with sudo:

    sudo -u openssl id

# Publish the release

## Update the source repositories

Finish up by pushing your local changes to the appropriate source repo as
instructed by `$TOOLS/release-tools/stage-release.sh`, which was performed
when [staging the releases](HOWTO-stage-a-release.md).  You may want to
sanity check the pushes by inserting the `-n` (dry-run) option.

## Upload release files to OpenSSL downloads

*BE CAREFUL*  This section makes everything visible and is therefore largely
irreversible.  If you are performing a dry run then DO NOT perform any steps
in this section.

*NOTE*  This section should only be performed for public releases, i.e.
releases made from `git@github.openssl.org:openssl/openssl.git` or
`git@github.com:openssl/security.git`.

Everything in this section is to be done as the `openssl` user on
`dev.openssl.org`, so if you haven't done that yet, you now *must* perform
the steps described in [SSH access](#ssh-access) above.

Check that the release has been uploaded properly.  The release tarballs and
associated files should be in `~openssl/dist/new`.  They should be owned by
the `upload` userid and world-readable.

Copy the tarballs to appropriate directories.  This can be done using the
do-release.pl script.  See `$TOOLS/release-tools/DO-RELEASE.md` for a
description of the options.  For example:

    perl ~openssl/do-release.pl --copy --move

This will copy the relevant files to the website and move them from
`~openssl/dist/new` to `~openssl/dist/old` so they will not seen by a
subsequent release.  Alternatively if you want to perform one release at a
time or copy/move the files manually, see below.

The `do-release.pl` script will display the commands you will need to issue
to send the announcement emails later.  Keep a note of those commands for
future reference.

Verify that the tarballs are available for download:

    ls /srv/ftp/source

## Upload release files to Github

Upload the release files to the "Releases" section on github.  Do this by
visiting the release URL that corresponds to the source repository that the
release was made from, or by using [the Github CLI tool](https://cli.github.com/]:

-   For releases from `git@github.openssl.org:openssl/openssl.git` or
    `git@github.com:openssl/security.git`:

    URL: https://github.com/openssl/openssl/releases

    GH CLI `--repo`: github.com/openssl/openssl

-   For releases from `git@github.openssl.org:openssl/premium.git`:

    URL: https://github.openssl.org/openssl/extended-releases/releases

    GH CLI `--repo`: github.openssl.org/openssl/openssl

In both tools, you will need to make a title and a short description.

For the title, use something like "OpenSSL 3.1.0".

For the release notes [^1], we currently use the same text as is added in the
`newsflash.md` file to announce the release
(see [Update the release data locally](#update-the-release-data-locally) below)

[^1]: The release notes field has previously been described as "description"

### Web method

Click the "Draft a new release" button.  Give the release a title and a
release note as recommended above.  Upload the four release files, e.g.

-   `openssl-3.1.0.tar.gz`
-   `openssl-3.1.0.tar.gz.asc`
-   `openssl-3.1.0.tar.gz.sha1`
-   `openssl-3.1.0.tar.gz.sha256`

If this is an alpha or beta release, check the "Set as a pre-release"
checkbox.

If this is the latest release version, check the "Set as the latest release"
checkbox.

Finish up by clicking "Publish release".

### GH CLI method

This is an example:

    gh release create \
        --repo github.com/openssl/openssl --verify-tag --draft \
        --title "OpenSSL 3.1.0" \
        --notes "Final version of OpenSSL 3.1.0 is now available: please download and upgrade!"
        openssl-3.1.0 \
        openssl-3.1.0.tar.gz \
        openssl-3.1.0.tar.gz.asc \
        openssl-3.1.0.tar.gz.sha1 \
        openssl-3.1.0.tar.gz.sha256 \

The first non-option argument `openssl-3.1.0` is the tag, the rest are the
files to upload.

If this is an alpha or beta release, additionally use the option `--prerelease`.

If this is the latest release version, additionally use `--latest`.

## Update the release metadata

*The changes in this section should be made in your clone of the release
data repo*

-   Newsflash *[only for public releases]*

    Update the newsflash.md file.  This normally is one or two lines.  Just
    copy and paste existing announcements making minor changes for the date
    and version number as necessary.  If there is an advisory then ensure
    you include a link to it.

-   Security advisory *[both public and premium releases]*

    Update the vulnerabilities.xml file if appropriate.

    If there is a Security Advisory then copy it into the secadv directory.

Make a pull request from your changes, against the release metadata repo
(the release metadata repo being `git@github.com:openssl/release-metadata.git`).
Await approval from reviewers, then merge the pull request.

# Post-publishing tasks

## Check automations

The updates performed when [publishing the releases](#publish-the-release),
automations on <https://automation.openssl.org/> should kick in.  Typically,
the builders named "doc" and "web" should be seen working within minutes
(pending other builder that mirror the repositories that have been updated).

These builders update different aspects of the web site, and will finish off
by invalidating the corresponding pages in the CDN cache, to ensure that
they are reloaded by the CDN.

You can also look at the result at <https://www-origin.openssl.org>.

## Check the website

Verify that the release notes, which are built from the CHANGES.md file
in the release, have been updated.  This is done automatically by OpenSSL
automation; if you see a problem, check if the web build job has been
performed yet, you may have to wait a few minutes before it kicks in.

Wait for a while for the CDN flush to work (normally within a few minutes).
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
-   <https://www.openssl.org/news/openssl-3.0-notes.html>
-   <https://www.openssl.org/news/openssl-3.1-notes.html>

## Send the announcement mail

Send out the announcements.  Generic release announcement messages will be
created automatically by the build script and the commands you need to use
to send them were displayed when you executed do-release.pl above. They
should be sent from the account of the person that owns the key used for
signing the release announcement. Ensure that mutt is configured correctly -
send a test email first if necessary.

If do-release.pl was used with `--move` be sure to move the announcement
text files away from the staging directory *after they have been sent*.
This is done as follows (with VERSION replaced with the version of OpenSSL
to announce):

    sudo -u openssl \
        mv ~openssl/dist/new/openssl-VERSION.txt.asc ~openssl/dist/old

## Send out the Security Advisory

*The secadv file mentioned in this section is the Security Advisory
that you copied into the release data repo, up in the section
[Update the release data locally](#update-the-release-data-locally)*

*This section is only applicable if this is a security release*

Start with signing the Security Advisory as yourself:

    gpg --clearsign secadv_FILENAME.txt

Then copy the result to the temporary directory on dev.openssl.org:

    scp secadv_FILENAME.txt.asc dev.openssl.org:/tmp

To finish, log in on dev.openssl.org and send the signed Security
Advisory by email as the user that signed the advisory.

For all releases, send it to the default set of public mailing lists,
replacing `YOU@openssl.org` with your email address:

    EMAIL="YOU@openssl.org" REPLYTO="openssl@openssl.org" \
        mutt -s "OpenSSL Security Advisory" \
            openssl-project openssl-users openssl-announce \
            </tmp/secadv_FILENAME.txt.asc

Finally, We also send it separately to oss-security (to avoid cross-posting
with our own lists), remember to replace `YOU@openssl.org` with your email
address:

    EMAIL="YOU@openssl.org" REPLYTO="openssl@openssl.org" \
        mutt -s "OpenSSL Security Advisory" \
            oss-security@lists.openwall.com \
            </tmp/secadv_FILENAME.txt.asc

For premium releases, send them to support-announce as well *and
separately*, remember to replace `YOU@openssl.org` with your email
address:

    EMAIL="YOU@openssl.org" REPLYTO="openssl@openssl.org" \
        mutt -s "OpenSSL Security Advisory" \
            support-announce </tmp/secadv_FILENAME.txt.asc

When done, remove the email file:

    rm /tmp/secadv_FILENAME.txt.asc

Approve the openssl-announce email.  Go to
<https://mta.openssl.org/mailman/admindb/openssl-announce>
and approve the messages.

For premium releases, approve the support-announce email as well.  Go to
<https://mta.openssl.org/mailman/admindb/support-announce> and approve the
messages.

Check that the mailing list messages have arrived.

## MITRE / CVE.org

If this release includes security fixes with a CVE then you should inform
MITRE about them.  See the instructions at the top of `cvepool.txt` in
`otc/security`.

Close the github advisory without pushing to github and remove the private
github fork if there was one.

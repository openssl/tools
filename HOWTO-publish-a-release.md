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
    -   [Publish GitHub release](#publish-github-release)
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

## Publish GitHub release

When a tag is pushed to the GitHub repository the automation creates a draft
release in https://github.com/openssl/openssl/releases. Check the signed
announcement .asc file. Check that the tarball length and hashes match in
the .md5, .sha1, .sha256.

For the release notes [^1], we currently use the same text as is added in the
`newsflash.md` file to announce the release.

[^1]: The release notes field has previously been described as "description"

If this is an alpha or beta release, check the "Set as a pre-release"
checkbox.

If this is the latest release version, check the "Set as the latest release"
checkbox.

Finish up by clicking "Publish release".

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

## Check the website

Verify that the release notes, which are built from the CHANGES.md file
in the release, have been updated.  This is done automatically by OpenSSL
automation; if you see a problem, check if the web build job has been
performed yet, you may have to wait a few minutes before it kicks in.

Wait for a while for the CDN flush to work (normally within a few minutes).

Check the download page has updated properly:

-   <https://openssl-library.org/source>

Check the notes look sensible at:

-   <https://openssl-library.org/news/newslog>

Also check the notes here:

-   <https://openssl-library.org/news/openssl-3.0-notes>
-   <https://openssl-library.org/news/openssl-3.1-notes>
-   <https://openssl-library.org/news/openssl-3.2-notes>
-   <https://openssl-library.org/news/openssl-3.3-notes>

## Send the announcement mail

Send out the announcements.  Generic release announcement messages will be
created automatically by the build script and the commands you need to use
to send them were displayed when you executed `do-release.pl` above. They
should be sent from the account of the person that owns the key used for
signing the release announcement.

## Send out the Security Advisory

*The secadv file mentioned in this section is the Security Advisory
that you copied into the release data repo*

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

Check that the mailing list messages have arrived.

## MITRE / CVE.org

If this release includes security fixes with a CVE then you should inform
MITRE about them.  See the instructions at the top of `cvepool.txt` in
`otc/security`.

Close the github advisory without pushing to github and remove the private
github fork if there was one.

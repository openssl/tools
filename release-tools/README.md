# HOW TO MAKE A RELEASE

This file documents how to make an OpenSSL release.  Please fix any
errors you find while doing, or just after, your next release!

Releases are done by one person, with a second person acting as the
reviewer and additional tester.

## Pre-requisites

Have a local clone of the website repo:

        openssl-git@git.openssl.org:openssl-web.git

Make sure you can sudo to the openssl user on dev.openssl.org; this is
usually done by being in the openssl group.  For example, ssh to the
server and run this command:

        sudo -u openssl id

## Setup

The day before the release, freeze the main repository.  This locks out
everyone but the named user, who is doing the release, from doing any pushes.
Someone other than the person doing the release should run the command.
For example:

        ssh openssl-git@git.openssl.org freeze openssl NAME

## Making the tarball and announcements

### Prepare the worktrees

This section generates the tarball and announcements locally.  It makes
no changes which cannot be easily undone.  You will have to repeat this
section for each version being released, so it is often easier to have
separate copies. The most effective way to do it is to have a single
working copy with several linked worktrees, one for each release branch.

        # clone a fresh working copy (only one for all worktrees)
        git clone openssl-git@git.openssl.org:openssl.git
        cd openssl

        # add a linked worktree (one for every release branch)
        git worktree add ../openssl-1.1.1 OpenSSL_1_1_1-stable
        cd ../openssl-1.1.1

If you are only releasing a single version, there is no need to have a
separate linked worktree. Just checkout the release branch in the working
copy when cloning:

        git clone -b OpenSSL_1_1_1-stable openssl-git@git.openssl.org:openssl.git

### Prepare the PATH variable

To simplify the release process, add the release-tools path (the directory
containing this README) to the PATH variable, to make the release tools
(`do-copyright-year, `mkrelease.pl`) available to the shell. For example,
if the release tools are located at $HOME/openssl/tools/release-tools, then

        export PATH=$HOME/openssl/tools/release-tools:$PATH

### For every release branch

The following procedure needs to be carried out for every release branch.

        cd ../openssl-1.1.1

Make sure that the CHANGES and NEWS files have been updated and reviewed.
NEWS should contain a summary of any changes for the release. For a security
release this is often just a list of the CVEs addressed. You should also
update NEWS in the master branch to include details of all releases. Just
update the NEWS bullet points - do not change the release date, keep it as
**under development**.

Add any security fixes to the tree. Commit them but *do not push*.

Make sure that the copyrights are updated.  This script will update
the copyright markers and commit the changes:

        do-copyright-year

Obtain approval for these commits from the reviewer and add the reviewed-by
headers as required.

Perform the local automated release steps. This can normally be done with:

        mkrelease.pl --reviewer=NAME

Alternatively, to use the openssl-team PGP key:

        export OPENSSL_GPG_KEYID=8B3D79F5
        mkrelease.pl --reviewer=NAME

See [MKRELEASE](MKRELEASE.md) for details of the options to `mkrelease.pl`.
This will leave a handful of files in the parent directory of where
you extracted the release.
See below for details of how to do perform this step manually if you want
to or have to.

Verify that the results of the script are sensible. Check
the commits the automated release process has performed, using for example
`git log`. Check the signed announcement RELEASE.asc file. Maybe check
that the tarball length and hashes match in the .md5, .sha1, and review
the announcment file. *Do not push* changes to the public repo at this stage.

Both the person doing the release and the reviewer should sanity-check the
release at this point. Checks to consider include the following:

- Builds and make test passes on multiple platforms - Linux, Windows, etc.
- Builds from tarball

Send the auto-generated commits to the reviewer and await their +1.
Repeat from the begining of this section if you need to release
multiple versions.

## Website updates

The changes in this section should be made in your copy of the web repo.

Update the `news/newsflash.txt` file. This normally is one or two lines. Just
copy and paste existing announcements making minor changes for the date and
version number as necessary. If there is an advisory then ensure you include a
link to it.

Update the `news/vulnerabilities.xml` file if appropriate.

If there is a Security Advisory then copy it into the `news/secadv` directory.

Commit your changes, but *do not push* them to the website.

## Publishing the release

*BE CAREFUL*  This section makes everything visible and is therefore
largely irreversible. If you are performing a dry run then DO NOT
perform any steps in this section.

Check that the release has been uploaded properly. The release tarballs and
associated files should be in `~openssl/dist/new`.  They should be owned by the
openssl userid and world-readable.

Copy the tarballs to appropriate directories. This can be
done using the `do-release.pl` script.  See [MKRELEASE](MKRELEASE.md) for a
description of the options. For example:

        sudo -u openssl perl ~openssl/do-release.pl --copy --move

This will copy the relevant files to the website and move them from
~openssl/dist/new to ~openssl/dist/old so they will not seen by a subsequent
release. Alternatively if you want to perform one release at a time or copy/move
the files manually, see below.

The do-release.pl script will display the commands you will need to issue to
send the announcement emails later. Keep a note of those commands for future
reference.

Verify that the tarballs are available via FTP:

        ftp://ftp.openssl.org/source/

And that they are ready for the website:

        ls /var/www/openssl/source

Push your local changes made above to the public repo. You will
typically want to sanity check this with:

        git push -n

Push new tags to public repo. Again sanity check with:

        git push --tags -n

to make sure no local tags were pushed.

##  Updating the website

Push the website changes you made earlier to the OpenSSL website repo.  When
you do this, the website will get updated and a script to flush the Akamai CDN
cache will be run.  You can look at things on www-origin.openssl.org; the
CDN-hosted www.openssl.org should only be a few minutes delayed.

Verify that the release notes, which are built from the CHANGES file in the
release, have been updated. This is done automatically by the commit-hook, but
if you see a problem, try the following steps:

        cd /var/www/openssl
        sudo -u openssl -H make relupd
        sudo -u openssl ./bin/purge-one-hour

Wait for a while for the Akamai flush to work (normally within a few minutes).
Have a look at the website and news announcement at:

        https://www.openssl.org/
        https://www.openssl.org/news/

Check the download page has updated properly:

        https://www.openssl.org/source/

Check the notes look sensible at:

        https://www.openssl.org/news/newslog.html

Also check the notes here:

        https://www.openssl.org/news/openssl-1.0.2-notes.html
        https://www.openssl.org/news/openssl-1.1.0-notes.html
        https://www.openssl.org/news/openssl-1.1.1-notes.html

## Send the announcement mail

Send out the announcements. Generic release announcement messages will be
created automatically by the build script and the commands you need to use to
send them were displayed when you executed do-release.pl above.
These should normally be sent from the openssl account. These are sent to
openssl-users, openssl-project, and openssl-announce.

If do-release.pl was used with `--move` be sure to move the
announcement text files away from the staging directory after they have been
sent.  This is done as follows (with VERSION replaced with the version of
OpenSSL to announce):

        sudo -u openssl \
            mv ~openssl/dist/new/openssl-VERSION.txt.asc ~openssl/dist/old

Send out the Security Advisory if there is one. Copy the file to the
openssl user home directory, and then do the following

        sudo -u openssl gpg -u 8B3D79F5 --clearsign secadv_FILENAME
        sudo -u openssl mutt -s "OpenSSL Security Advisory" \
                openssl-project openssl-users openssl-announce \
                <~openssl/secadv_FILENAME.txt.asc

Approve the openssl-announce email.  Go to
<https://mta.openssl.org/mailman/admindb/openssl-announce>
and approve the messages.
The administration password needed for approval is held in /opt/mailman/README
on mta.openssl.org

Check the mailing list messages have arrived.

## Finish

Unfreeze the repository.

        ssh openssl-git@git.openssl.org unfreeze openssl

If this release includes security fixes with a CVE then you should inform
MITRE about them. See the instructions at the top of cvepool.txt in omc.

Check mailing lists over the next few hours for reports of any success
or failure. If necessary fix these and in the worst case make another
release.

# MANUAL PROCESS

If for some reason you cannot use, or do not trust, release script
mkrelease.pl then you can perform the release manually.  This is difficult to
get right so you should avoid it if possible.

Check what the automated release did for previous releases. This is the best
way to get a feel for what happens. You can do this by checking the commit
logs before a release tag for example:

        git log --reverse 0d7717f..ebe2219

The first two commits are security fixes. The third commit is (as the log
message implies) an update of the NEWS file. The next commit which has the
automated log message "Prepare for 1.0.1g release" includes the steps
necessary to make the release.

## Manually building the release files

Do a `make update`. If necessary commit. You can push this commit to
the repo so you have as few local changes as possible. Note that even if
"make update" does not make any visible changes it can still update timestamps
on some files which avoid some problems with builds (e.g. if the source files
are all made read only).

Update NEWS, README and CHANGES. These should contain the date and
the correct version in the appropriate format.

Update crypto/opensslv.h which contains the version. This contains the
version number in the appropriate formats. For OPENSSL_VERSION_NUMBER and
normal (not pre) releases you change the last digit from 0 (meaning -dev)
to f (meaning release). Change the text forms in OPENSSL_VERSION_TEXT for
normal and FIPS builds.

Double-check that the version is right. If you mess up the syntax you can end
up with the wrong release number or worse break compilation.

Commit the changes you made so far, and check that the logs look sensible.

Make a local tag; the public repo requires annotated tags:

        git tag -s -m "OpenSSL 1.0.2L release tag" OpenSSL_1_0_2L

or if you want to use the openssl-team key:

        git tag -u 8B3D79F5 -m "OpenSSL 1.0.2L release tag" OpenSSL_1_0_2L

Make the release tarball. You do this with:

        make tar

Create .sha1, .sha256 and .asc files manually. You can use:

        openssl sha1
        openssl sha256

Create .sha1, .sha256 and .asc files manually. You can use the openssl sha1 and
sha256 commands, obviously. Sign the tarball:

        gpg -sba opensslversion.tar.gz

or if you want to use the openssl-team key:

        gpg -u 8B3D79F5 -sba opensslversion.tar.gz

Create an announcement file. You can use an existing one as a
template for example something in ~openssl/dist/old/ update the version
numbers, tarball size and hashes. Sign announcement with:

        gpg -sta --clearsign announce.txt

or if you want to use the openssl-team key:

        gpg -u 8B3D79F5 -sta --clearsign announce.txt

Prepare for next development version by updating CHANGES, NEWS, README
crypto/opensslv.h and openssl.spec. The automated scripts use the comment
message `Prepare for 1.0.1h-dev`.

Be absolutely *certain* you did not make any mistakes, so check
several times preferably by different people.

Upload tarballs to dev.openssl.org

## Manually releasing the files

If you do not want to use do-release.pl, you can manually perform
the steps necessary for the release. This is (fortunately) much simpler
than the manual release process above.

Copy release files to web source directory. The four files (tarball,
sha1, .sha256 and .asc) need to be manually copied to /var/www/openssl/source
Also move any outdated releases to /var/www/openssl/source/old/SUBDIR

Copy files to ftp source directory, /srv/ftp/source.
Also move any oudated releases to /srv/ftp/source/old/SUBDIR

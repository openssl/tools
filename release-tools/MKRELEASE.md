# Documentation on the mkrelease.pl script

**NOTE**: this script is unsuitable for OpenSSL 3.0 and on.  Instead, use
the `dev/release.sh` script found in the source.  That script has a built
in manual; `dev/release.sh --help` gives a quick usage summary, while
`dev/release.sh --manual` displays a man-page.

This file provides an overview of the mkrelease.pl script, and how to
configure some of its parameters (by setting environment variables).
It is normally run by following the process in README.md and should be
run in a pristine directgory of the branch to be released, which must
be a stable branch.

The script handles most of the processes involved in making a release
including:

1. Doing `make update`
2. Changing version numbers in various files
3. Tagging release
4. Making the tarballs, .md5, .sha1, .sha256 and .gpg files
5. Creating the signed email announcement, including hashes of release
6. Uploading files to dev.openssl.org
7. Updating the version for next release

If you plan to make an actual release make sure your GPG key is included
in the [OMC list](https://www.openssl.org/community/omc.html) on the website
and in the file doc/fingerprints.txt of *all* active branches.

The script mkrelease.pl calls the files release-check.pl, release-date.pl,
release-git.pl, release-update.pl and release-version.pl, which are expected
to all be in the same directory.

You are advised to clone a fresh repository. Unless you specify `--no-clean`
the release process will run `git clean -x -d -f`
*WARNING* this will delete ALL untracked files from the current branch.

From the branch directory if you run:

        perl /path/to/mkrelease.pl --reviewer=name

It should perform all of the above steps and commit changes locally. You can
then sanity check these with `git log` before pushing them to the public repo.

## Environment Variables

- OPENSSL<br>
  Path to openssl utility to use. Default is `openssl`.

- OPENSSL_TAR<br>
  The tar command to use when creating the tarball. Default is `tar`.

- OPENSSL_GPG<br>
  The gpg command to use when signing a tarball or announcement.
  The default is `gpg` which will use gpg with the default key.
  If you wish to use a different, key set OPENSSL_GPG to include
  appropriate options.

- OPENSSL_GPG_TAR<br>
  Command to use to sign a tarball.
  The default is: `$OPENSSL_GPG --use-agent -sba`

- OPENSSL_GPG_ANNOUNCE<br>
  The command to use to sign a tarball.
  The default is: `$OPENSSL_GPG --use-agent -sta --clearsign`

- OPENSSL_SCP<br>
  The command to use to upload files.
  The default is `scp`

- OPENSSL_SCP_HOST<br>
  The host (and optional username) needed to upload files.
  The default is `dev.openssl.org`, but you might want to change this to
  `username@dev.openssl.org`

- OPENSSL_SCP_DIR<br>
  The directory to upload files to.
  Normally this wont be changed from the default which is
  `$OPENSSL_SCP_HOST:~openssl/dist/new`
  This is a holding area on dev.openssl.org where distributions are uploaded
  temporarily before being moved to the web and ftp directories.

For local testing, you can do something like this:

        export OPENSSL_SCP=cp
        export OPENSSL_SCP_DIR="$HOME/testdir"

## Options

- `--revert`<br>
  Remove all local changes from repository and delete any release tag. This
  returns the local tree to the same state as before a release attempt was
  made.

- `--reviewer=name`<br>
  Add reviewer `name` to list of reviewers in commit message. Any valid
  name for checking OMC membership will work.
  This option may be used multiple times; at least one is required.

- `--enter-pre`<br>
  Instead of making a full release enter pre-release state. This by itself
  will not produce a release it will just change version numbers and commit
  the changes. Subsequent releases on this branch will be pre-release
  versions. This option should NOT be used if the branch is already in
  pre-release state.

- `--leave-pre`<br>
  For a branch in pre-release state, leave pre-release and make a full release.

- `--label=label`<br>
   Add the textual label `label` to the version string, where `label` must be
   one of `alpha` or `beta`. While in pre-release state a label *must* be
   provided.

- `--no-upload`<br>
  Do not attempt to upload release files to dev.openssl.org

- `--no-clean`<br>
  Do not clean untracked files from directory. Warning: if you use this option
  you can end up with extraneous files in the distribution tarball.

- `--no-update`<br>
  Do not perform a `make update`.

- `--verbose`<br>
  Be more verbose at what is going on

- `--debug`<br>
  Include debug output to describe all actions in detail

- `--git-info`<br>
  Just print out details of all git branch information and exit

- `--git-branch-info`<br>
  Print out details of the currently detected branch and exit

- `--branch-version=version`<br>
  Use branch `version` instead of the one autodetected for the current branch.
  This option is not normally needed.

# The do-release script

The do-release.pl script copies distributions from the temporary holding area
to the http and ftp areas. It it intended to be run as the `openssl` user on
dev.openssl.org.

It does the following:

1. Copy OpenSSL release files from the holding area to the http and ftp
   locations: currently /v/openssl/www/source and /v/openssl/ftp/source
2. Move OpenSSL release files from holding area to ~openssl/dist/old By
   doing this the script wont try and make a release again with old files.
3. Mail the release message. This is sent to openssl-dev openssl-users and
   openssl-announce (it needs to be approved in openssl-announce). The
   subject line is `OpenSSL version xxx released`.

## do-release options

- `--copy`<br>
  Copy files to http and ftp directories.  **You will have to manually move
  the OLD files to old/<SUBDIR> directories.**

- `--move`<br>
  Move files from holding area to ~openssl/dist/old

- `--mail`<br>
  Send out announcement email: if this option is not given, the command you
  need to call to send the release mail will be printed out.

- `--full-release`<br>
  Perform all operations for a release (copy, move and mail).

Note: because several of these options are irreversible they have to be
explicitly included.

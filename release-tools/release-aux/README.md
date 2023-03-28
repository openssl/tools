Auxillary files for dev/release.sh
===================================

- `release-state-fn.sh`

  This is the main version and state update logic...  you could say
  that it's the innermost engine for the release mechanism.  It
  tries to be agnostic of versioning schemes, and relies on
  release-version-fn.sh to supply necessary functions that are
  specific for versioning schemes.

- `release-version-fn.sh`

  Supplies functions to manipulate version data appropriately for the
  detected version scheme:

  `get_version()` gets the version data from appropriate files.

  `set_version()` writes the version data to appropriate files.

  `fixup_version()` updates the version data, given a first argument
  that instructs it what update to do.

  `std_branch_name()` outputs the standard branch name for the OpenSSL
  version in the worktree.

  `std_tag_name()` outputs the standard tag name for the the OpenSSL
  version in the worktree.

- `openssl-announce-pre-release.tmpl` and `openssl-announce-release.tmpl`

  Templates for announcements

- `fixup-*-release.pl` and `fixup-*-postrelease.pl`

  Fixup scripts for specific files, to be done for the release
  commit and for the post-release commit.

  Some of the scripts have very similar names, to handle different file layouts.
  For example, `fixup-CHANGES.md-postrelease.pl` handles the file `CHANGES.md`
  that is used in OpenSSL 3.0 and on, while `fixup-CHANGES-postrelease.pl`
  handles the file `CHANGES` that is used in pre-3.0 OpenSSL versions.
  Do not confuse these or other similarly named scripts.

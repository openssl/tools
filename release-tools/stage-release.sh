#! /usr/bin/env bash
# Copyright 2020-2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

set -e

# This is the most shell agnostic way to specify that POSIX rules.
POSIXLY_CORRECT=1

# Force C locale because some commands (like date +%b) relies
# on the current locale.
export LC_ALL=C

usage () {
    cat <<EOF
Usage: stage-release.sh [ options ... ]

--alpha         Start or increase the "alpha" pre-release tag.
--next-beta     Switch to the "beta" pre-release tag after alpha release.
                It can only be given with --alpha.
--beta          Start or increase the "beta" pre-release tag.
--final         Get out of "alpha" or "beta" and make a final release.

--reviewer=<id> The reviewer of the commits.

--quiet         Really quiet, only the final output will still be output.
--verbose       Verbose output.
--debug         Include debug output.
--porcelain     Give the output in an easy-to-parse format for scripts.

--help          This text
--manual        The manual

If none of --alpha, --beta, or --final are given, this script tries to
figure out the next step.

The worktree this script runs in must be clean -- the script operates on
the current branch directly and produces release artifacts in the parent
directory.  Upload of those artifacts is out of scope; the caller is
responsible for shipping them.
EOF
    exit 0
}

# Set to one of 'major', 'minor', 'alpha', 'beta' or 'final'
next_method=
next_method2=

# Always try to create the release branch.  The post-arg-parsing
# logic below resets this to false when we're already on a release
# branch or when PATCH != 0, so passing --branch was redundant.
do_branch=true

ECHO=echo
DEBUG=:
VERBOSE=:
git_quiet=-q
do_porcelain=false

do_help=false
do_manual=false

reviewers=

TEMP=$(getopt -l 'alpha,next-beta,beta,final' \
              -l 'reviewer:' \
              -l 'quiet,verbose,debug' \
              -l 'porcelain' \
              -l 'help,manual' \
              -n stage-release.sh -- - "$@")
eval set -- "$TEMP"
while true; do
    case $1 in
    --alpha | --beta | --final )
        next_method=$(echo "x$1" | sed -e 's|^x--||')
        if [ -z "$next_method2" ]; then
            next_method2=$next_method
        fi
        shift
        ;;
    --next-beta )
        next_method2=$(echo "x$1" | sed -e 's|^x--next-||')
        shift
        ;;
    --reviewer )
        reviewers="$reviewers $1=$2"
        shift
        shift
        ;;
    --quiet )
        ECHO=:
        VERBOSE=:
        shift
        ;;
    --verbose )
        ECHO=echo
        VERBOSE=echo
        git_quiet=
        shift
        ;;
    --debug )
        DEBUG=echo
        shift
        ;;
    --porcelain )
        do_porcelain=true
        shift
        ;;
    --help )
        usage
        exit 0
        ;;
    --manual )
        sed -e '1,/^### BEGIN MANUAL/d' \
            -e '/^### END MANUAL/,$d' \
            < "$0" \
            | pod2man \
            | man -l -
        exit 0
        ;;
    -- )
        shift
        break
        ;;
    * )
        echo >&2 "Unknown option $1"
        shift
        exit 1
        ;;
    esac
done

$DEBUG >&2 "DEBUG: \$next_method=$next_method"
$DEBUG >&2 "DEBUG: \$next_method2=$next_method2"

$DEBUG >&2 "DEBUG: \$do_branch=$do_branch"

$DEBUG >&2 "DEBUG: \$DEBUG=$DEBUG"
$DEBUG >&2 "DEBUG: \$VERBOSE=$VERBOSE"
$DEBUG >&2 "DEBUG: \$git_quiet=$git_quiet"

case "$next_method+$next_method2" in
    major+major | minor+minor )
        # These are expected
        ;;
    alpha+alpha | alpha+beta | beta+beta | final+final | + | +beta )
        # These are expected
        ;;
    * )
        echo >&2 "Internal option error ($next_method, $next_method2)"
        exit 1
        ;;
esac

# Verbosity feed for certain commands
VERBOSITY_FIFO=/tmp/openssl-$$.fifo
mkfifo -m 600 $VERBOSITY_FIFO
( cat $VERBOSITY_FIFO | while read L; do $VERBOSE "> $L"; done ) &
exec 42>$VERBOSITY_FIFO
trap "exec 42>&-; rm $VERBOSITY_FIFO" 0 2

# Setup ##############################################################

RELEASE_TOOLS=$(dirname $(realpath $(type -p $0)))
RELEASE_AUX="$RELEASE_TOOLS/release-aux"

# Check that we have external scripts that we use
found=true
for fn in "$RELEASE_TOOLS/do-copyright-year"; do
    if ! [ -f "$fn" ]; then
        echo >&2 "'$fn' is missing"
        found=false
    fi
done
if ! $found; then
    exit 1
fi

# Check that we have the scripts that define functions we use
found=true
for fn in "$RELEASE_AUX/release-version-fn.sh" \
          "$RELEASE_AUX/release-state-fn.sh" \
          "$RELEASE_AUX/release-data-fn.sh"; do
    if ! [ -f "$fn" ]; then
        echo >&2 "'$fn' is missing"
        found=false
    fi
done
if ! $found; then
    exit 1
fi

# Load version functions
. $RELEASE_AUX/release-version-fn.sh
. $RELEASE_AUX/release-state-fn.sh
. $RELEASE_AUX/release-data-fn.sh

# Make sure we're in the work directory, and remember it
if HERE=$(git rev-parse --show-toplevel); then
    :
else
    echo >&2 "Not in a git worktree"
    exit 1
fi

# Make sure that it's a plausible OpenSSL work tree, by checking
# that a version file is found
get_version

if [ -z "$VERSION_FILE" ]; then
    echo >&2 "Couldn't find OpenSSL version data"
    exit 1
fi

orig_HEAD=$(git rev-parse HEAD)
orig_branch=$(git rev-parse --abbrev-ref HEAD)
orig_remote=$(git for-each-ref --format='%(push:remotename)' \
                  $(git symbolic-ref -q HEAD))
if ! orig_remote_url=$(git remote get-url $orig_remote 2>/dev/null); then
    # If there is no registered remote, then $orig_remote is the URL
    orig_remote_url="$orig_remote"
fi
orig_head=$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null || git rev-parse HEAD)

# Make sure it's a branch we recognise
if (echo "$orig_branch" \
        | grep -E -q \
               -e '^master$' \
               -e '^OpenSSL_[0-9]+_[0-9]+_[0-9]+[a-z]*-stable$' \
               -e '^openssl-[0-9]+\.[0-9]+$'); then
    :
else
    echo >&2 "Not in master or any recognised release branch"
    echo >&2 "Please 'git checkout' an appropriate branch"
    exit 1
fi

# Make sure that we have fixup scripts for all the files that need
# to be modified for a release.  We trust this, because we're not
# going to change versioning scheme in the middle of a release.
save_IFS=$IFS
IFS=';'
found=true
for fn in $RELEASE_FILES; do
    for file in "$RELEASE_AUX/fixup-$fn-release.pl" \
                "$RELEASE_AUX/fixup-$fn-postrelease.pl"; do
        if ! [ -f "$file" ]; then
            echo >&2 "'$file' is missing"
            found=false
        fi
    done
done
IFS=$save_IFS
if ! $found; then
    exit 1
fi

# Initialize #########################################################

$ECHO "== Initializing work tree"

# This script operates on the current branch directly, so refuse to run
# if the worktree is dirty.  Jenkins jobs run in a fresh workspace, so
# in practice this is just a sanity check.
if [ -n "$(git status -s)" ]; then
    echo >&2 "Worktree is not clean; refusing to run"
    exit 1
fi

get_version

# Branches to start from.  The release branch is where the changes for the
# release are made, and the update branch is where the post-release changes are
# made.  When releasing from master at PATCH == 0 they differ (the update
# branch stays as master, the release branch becomes openssl-X.Y); otherwise
# they are the same.
orig_update_branch="$orig_branch"
orig_release_branch="$(std_branch_name)"

# We create a release branch only when we're on master at PATCH == 0;
# otherwise (already on a release branch, or this is a patch release)
# we make the release commit on the current branch.
if [ "$orig_update_branch" = "$orig_release_branch" ] \
       || [ -n "$PATCH" -a "$PATCH" != 0 ]; then
    do_branch=false
fi

if ! $do_branch; then
    # The computed release branch may differ from the update branch when
    # alpha or beta releases are made on master, which is fine -- in that
    # case we keep operating on the current branch.
    orig_release_branch="$orig_update_branch"
fi

# Sanity check: we should still be on the branch the worktree started
# on (or, after a --branch switch later in the script, on the release
# branch).
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$orig_update_branch" ] \
       && [ "$current_branch" != "$orig_release_branch" ]; then
    echo >&2 "Unexpected current branch: $current_branch"
    exit 1
fi

SOURCEDIR=$(pwd)
$DEBUG >&2 "DEBUG: Source directory is $SOURCEDIR"

# Release ############################################################

# We always expect to start from a state of development
if [ "$TYPE" != 'dev' ]; then
    cat >&2 <<EOF
Not in a development branch.

Have a look at the git log, it may be that a previous crash left it in
an intermediate state and that need to drop the top commit:

git reset --hard $orig_head
# WARNING! LOOK BEFORE YOU ACT, KNOW WHAT YOU DO
EOF
    exit 1
fi

# Update the version information.  This won't save anything anywhere, yet,
# but does check for possible next_method errors before we do bigger work.
next_release_state "$next_method"

# Standard branch and tag names.  The update branch is where the
# post-release bump commit lands; the release branch is where the
# release commit + tag live, which differs from the update branch
# only when --branch was given and is effective.
update_branch="$orig_update_branch"
release_branch="$orig_release_branch"
release_tag="$(std_tag_name)"

$VERBOSE "== Checking source file copyright year updates"

$RELEASE_TOOLS/do-copyright-year
if [ -n "$(git status --porcelain --untracked-files=no --ignore-submodules=all)" ]; then
    $VERBOSE "== Committing copyright year updates"
    git add -u
    git commit $git_quiet -m $'Copyright year updates\n\nRelease: yes'
    if [ -n "$reviewers" ]; then
        addrev --release --nopr $reviewers
    fi
fi

$ECHO "== Configuring OpenSSL for update and release.  This may take a bit of time"

./Configure cc >&42

$VERBOSE "== Checking source file updates and fips checksums"

make update >&42
# As long as we're doing an alpha release, we can have symbols without specific
# numbers assigned. In a beta or final release, all symbols MUST have an
# assigned number.
if [ "$next_method" != 'alpha' ] && grep -q '^renumber *:' Makefile; then
    make renumber >&42
fi
if grep -q '^update-fips-checksums *:' Makefile; then
    make clean >&42
    make update-fips-checksums >&42
fi

if [ -n "$(git status --porcelain --untracked-files=no --ignore-submodules=all)" ]; then
    $VERBOSE "== Committing updates"
    git add -u
    git commit $git_quiet -m $'make update\n\nRelease: yes'
    if [ -n "$reviewers" ]; then
        addrev --release --nopr $reviewers
    fi
fi

# Create a update branch, unless it's the same as the update branch
if [ "$release_branch" != "$update_branch" ]; then
    $VERBOSE "== Creating a local release branch and switch to it: $release_branch"
    git checkout $git_quiet -b "$release_branch"
fi

# Write the version information we updated
set_version

release="$FULL_VERSION"
if [ -n "$PRE_LABEL" ]; then
    release_text="$SERIES$_BUILD_METADATA $PRE_LABEL $PRE_NUM"
else
    release_text="$release"
fi
$VERBOSE "== Updated version information to $release"

$VERBOSE "== Updating files with release date for $release : $RELEASE_DATE"
(
    IFS=';'
    for file in $RELEASE_FILES; do
        fixup="$RELEASE_AUX/fixup-$(basename "$file")-release.pl"
        $VERBOSE "> $file"
        RELEASE="$release" RELEASE_TEXT="$release_text" RELEASE_DATE="$RELEASE_DATE" \
               perl -pi $fixup $file
    done
)

$VERBOSE "== Committing updates and tagging"
git add -u
git commit $git_quiet -m "Prepare for release of $release_text"$'\n\nRelease: yes'
if [ -n "$reviewers" ]; then
    addrev --release --nopr $reviewers
fi
$ECHO "Tagging release with tag $release_tag."
# Annotated, never signed.  The signing key lives on an HSM that only
# hsm-client can reach, and this script runs on the build host, so the tag is
# re-signed afterwards by whoever has that access -- `git tag -s -f` over the
# same commit, then the tarball with `sq-pkcs11 sign`.  Keeping the two apart
# is what lets staging run without any HSM at all.
git tag -a "$release_tag" -m "OpenSSL $release release tag"

tarfile=openssl-$release.tar
tgzfile=$tarfile.gz
metadata=openssl-$release.dat

$ECHO "== Generating tar, hash, and metadata files."
$ECHO "== This may take a bit of time..."

$VERBOSE "== Making tarfile: $tgzfile"

# Unfortunately, some tarball generators do verbose output on STDERR...  for
# good reason, but it means we don't display errors unless --verbose
(
    if [ -f ./util/mktar.sh ]; then
        ./util/mktar.sh --tarfile="../$tarfile" 2>&1
    else
        make DISTTARVARS=TARFILE="../$tarfile" dist 2>&1
    fi
) | while read L; do $VERBOSE "> $L"; done

if ! [ -f "../$tgzfile" ]; then
    echo >&2 "Where did the tarball end up? (../$tgzfile)"
    exit 1
fi

$VERBOSE "== Generating checksums: $tgzfile.sha1 $tgzfile.sha256"
sha1hash=$(openssl sha1 < "../$tgzfile" | \
    (IFS='= '; while read X H; do echo $H; done))
sha256hash=$(openssl sha256 < "../$tgzfile" | \
    (IFS='= '; while read X H; do echo $H; done))

echo "$sha1hash *$tgzfile" > "../$tgzfile.sha1"
echo "$sha256hash *$tgzfile" > "../$tgzfile.sha256"

# No signature is produced here, but a stale one from an earlier run must not
# survive: the tarball has just been rebuilt, so any existing .asc alongside it
# now attests to different bytes.
rm -f "../$tgzfile.asc"

release_files=( "$tgzfile" "$tgzfile.sha1" "$tgzfile.sha256" )

$VERBOSE "== Generating metadata file: $metadata"

(
    set -x
    echo "update_branch='$orig_update_branch'"
    if [ "$release_branch" != "$update_branch" ]; then
        echo "release_branch='$orig_release_branch'"
    fi
    echo "release_tag='$release_tag'"
    echo "release_files='${release_files[@]}'"
    echo "source_repo='$orig_remote_url'"
) > ../$metadata

# Post-release #######################################################

# Reset the files to their pre-release contents.  This doesn't affect
# HEAD, but simply set all the files in a state that 'git revert -n HEAD'
# would have given, but without the artifacts that 'git revert' adds.
#
# This allows all the post-release fixup scripts to perform from the
# same point as the release fixup scripts, hopefully making them easier
# to write.  This also makes the same post-release fixup scripts easier
# to run when --branch has been used, as they will be run both on the
# release branch and on the update branch, essentially from the same
# state for affected files.
$VERBOSE "== Reset all files to their pre-release contents"
git reset $git_quiet HEAD^ -- .
git checkout -- .

prev_release_text="$release_text"
prev_release_date="$RELEASE_DATE"

next_release_state "$next_method2"
set_version

release="$FULL_VERSION"
release_text="$VERSION$_BUILD_METADATA"
if [ -n "$PRE_LABEL" ]; then
    release_text="$SERIES$_BUILD_METADATA $PRE_LABEL $PRE_NUM"
fi
$VERBOSE "== Updated version information to $release"

$VERBOSE "== Updating files for $release :"
(
    IFS=';'
    for file in $RELEASE_FILES; do
        fixup="$RELEASE_AUX/fixup-$(basename "$file")-postrelease.pl"
        $VERBOSE "> $file"
        RELEASE="$release" RELEASE_TEXT="$release_text" \
               PREV_RELEASE_TEXT="$prev_release_text" \
               PREV_RELEASE_DATE="$prev_release_date" \
               perl -pi $fixup $file
    done
)

$VERBOSE "== Committing updates"
git add -u
git commit $git_quiet -m "Prepare for $release_text"$'\n\nRelease: yes'
if [ -n "$reviewers" ]; then
    addrev --release --nopr $reviewers
fi

if [ "$release_branch" != "$update_branch" ]; then
    $VERBOSE "== Going back to the update branch $update_branch"
    git checkout $git_quiet "$update_branch"

    get_version
    next_release_state "minor"
    set_version

    release="$FULL_VERSION"
    release_text="$SERIES$_BUILD_METADATA"
    $VERBOSE "== Updated version information to $release"

    $VERBOSE "== Updating files for $release :"
    (
        IFS=';'
        for file in $RELEASE_FILES; do
            fixup="$RELEASE_AUX/fixup-$(basename "$file")-postrelease.pl"
            $VERBOSE "> $file"
            RELEASE="$release" RELEASE_TEXT="$release_text" \
                   perl -pi $fixup $file
        done
    )

    $VERBOSE "== Committing updates"
    git add -u
    git commit $git_quiet -m "Prepare for $release_text"$'\n\nRelease: yes'
    if [ -n "$reviewers" ]; then
        addrev --release --nopr $reviewers
    fi
fi

# Done ###############################################################

$VERBOSE "== Done"

cd $HERE
if $do_porcelain; then
    echo "orig_head='$orig_head'"
    echo "metadata='$metadata'"
else
    cat <<EOF

======================================================================
The release is done.  The release artifacts and a metadata file have
been written to the parent directory; pushing the commits and tag and
shipping the artifacts are the caller's responsibility.
======================================================================

The following files were generated:

EOF
    for uf in "${release_files[@]}"; do
        echo "    $uf"
    done
    cat <<EOF

----------------------------------------------------------------------

EOF

    if [ "$release_branch" != "$update_branch" ]; then
        cat <<EOF
A release tag and a release branch have been added to the worktree,
and the current branch has been updated.

    Updated branch: $update_branch
    Release branch: $release_branch
    Tag: $release_tag

When pushing everything to the main repository, do it like this:

    git push git@github.openssl.org:openssl/openssl.git \\
        $release_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $update_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $release_tag
EOF
    else
        cat <<EOF
A release tag has been added to the worktree, and the current branch
has been updated.

    Release/update branch: $update_branch
    Tag: $release_tag

When pushing everything to the main repository, do it like this:

    git push git@github.openssl.org:openssl/openssl.git \\
        $update_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $release_tag
EOF
    fi

    cat <<EOF

----------------------------------------------------------------------
EOF
fi

exit 0

# cat is inconsequential, it's only there to fend off zealous shell parsers
# that parse all the way here.
cat <<EOF
### BEGIN MANUAL
=pod

=head1 NAME

stage-release.sh - OpenSSL release staging script

=head1 SYNOPSIS

B<stage-release.sh>
[
B<--alpha> |
B<--next-beta> |
B<--beta> |
B<--final> |
B<--reviewer>=I<id> |
B<--quiet> |
B<--verbose> |
B<--debug> |
B<--porcelain> |
B<--help> |
B<--manual>
]

=head1 DESCRIPTION

B<stage-release.sh> creates an OpenSSL release, given current worktree
conditions.  It will refuse to work unless the current branch is C<master>
or a release branch (see L</RELEASE BRANCHES AND TAGS> below for a
discussion on those).

B<stage-release.sh> tries to be smart and figure out the next release if no
hints are given through options, and will exit with an error in ambiguous
cases.

B<stage-release.sh> normally finishes off with instructions on what to do
next.  When B<--porcelain> is given, it finishes off with script friendly
data instead, see the description of that option.  When finishing commands
are given, they must be followed exactly.

B<stage-release.sh> operates on the current worktree directly: it
refuses to run if the worktree is not clean, and updates the current
branch in place.  The release artifacts (tarball, hashes, metadata) are
written to the parent directory.  Signing them, pushing the resulting
commits and tag, and shipping the artifacts, are the caller's
responsibility -- nothing is signed, uploaded or pushed by this script.

The release tag is annotated, not signed: the signing key is held on an
HSM that the build host cannot reach, so signing the tag and the tarball
is a separate step, run where that access exists.

=head1 OPTIONS

=over 4

=item B<--alpha>, B<--beta>

Set the state of this branch to indicate that alpha or beta releases are
to be done.

B<--alpha> is only acceptable if the I<PATCH> version number is zero and
the current state is "in development" or that alpha releases are ongoing.

B<--beta> is only acceptable if the I<PATCH> version number is zero and
that alpha or beta releases are ongoing.

=item B<--next-beta>

Use together with B<--alpha> to switch to beta releases after the current
release is done.

=item B<--final>

Set the state of this branch to indicate that regular releases are to be
done.  This is only valid if alpha or beta releases are currently ongoing.

=item B<--reviewer>=I<id>

Add I<id> to the set of reviewers for the commits performed by this script.
Multiple reviewers are allowed.

If no reviewer is given, you will have to run C<addrev> manually, which
means retagging a release commit manually as well.

=item B<--quiet>

Really quiet, only bare necessity output, which is the final instructions,
or should the B<--porcelain> option be used, only that output.

messages appearing on standard error will still be shown, but should be
fairly minimal.

=item B<--verbose>

Verbose output.

=item B<--debug>

Display extra debug output.

=item B<--porcelain>

Give final output in an easy-to-parse format for scripts.  The output comes
in a form reminicent of shell variable assignments.  Currently supported are:

=over 4

=item B<metadata>=I<file>

The metadata file.  See L</FILES> for a description of all generated files
as well as the contents of the metadata file.

=back

=item B<--help>

Display a quick help text and exit.

=item B<--manual>

Display this manual and exit.

=back

=head1 RELEASE BRANCHES AND TAGS

Prior to OpenSSL 3.0, the release branches were named
C<< OpenSSL_I<SERIES>-stable >>, and the release tags were named
C<< OpenSSL_I<VERSION> >> for regular releases, or
C<< OpenSSL_I<VERSION>-preI<n> >> for pre-releases.

From OpenSSL 3.0 ongoing, the release branches are named
C<< openssl-I<SERIES> >>, and the release tags are named
C<< openssl-I<VERSION> >> for regular releases, or
C<< openssl-I<VERSION>-alphaI<n> >> for alpha releases
and C<< openssl-I<VERSION>-betaI<n> >> for beta releases.

B<stage-release.sh> recognises both forms.

=head1 VERSION AND STATE

With OpenSSL 3.0, all the version and state information is in the file
F<VERSION.dat>, where the following variables are used and changed:

=over 4

=item B<MAJOR>, B<MINOR>, B<PATCH>

The three part of the version number.

=item B<PRE_RELEASE_TAG>

The indicator of the current state of the branch.  The value may be one pf:

=over 4

=item C<dev>

This branch is "in development".  This is typical for the C<master> branch
unless there are ongoing alpha or beta releases.

=item C<< alphaI<n> >> or C<< alphaI<n>-dev >>

This branch has alpha releases going on.  C<< alphaI<n>-dev >> is what
should normally be seen in the git workspace, indicating that
C<< alphaI<n> >> is in development.  C<< alphaI<n> >> is what should be
found in the alpha release tar file.

=item C<< alphaI<n> >> or C<< alphaI<n>-dev >>

This branch has beta releases going on.  The details are otherwise exactly
as for alpha.

=item I<no value>

This is normally not seen in the git workspace, but should always be what's
found in the tar file of a regular release.

=back

=item B<BUILD_METADATA>

Extra build metadata to be used by anyone for their own purposes.

=item B<RELEASE_DATE>

This is normally empty in the git workspace, but should always have the
release date in the tar file of any release.

=back

=head1 FILES

The following files are produced in the parent directory of the
worktree.  Shipping them is the caller's responsibility; this script
does not upload anything.

=over 4

=item F<openssl-{VERSION}.tar.gz>

The source tarball itself.

=item F<openssl-{VERSION}.tar.gz.sha1>, F<openssl-{VERSION}.tar.gz.sha256>

The SHA1 and SHA256 checksums for F<openssl-{VERSION}.tar.gz>.

=item F<openssl-{VERSION}.dat>

The metadata file for F<openssl-{VERSION}.tar.gz>.  It contains shell
variable assignments with data that may be of interest for other scripts,
such as a script to promote this release to an actual release:

=over 4

=item B<update_branch>=I<branch>

The update branch.  This is always given.

=item B<release_branch>=I<branch>

The release branch, if a new one was created (i.e. when releasing from
C<master> at PATCH == 0).  Omitted when the release commit is made on
the current branch.

=item B<release_tag>=I<tag>

The release tag.  This is always given.

=item B<release_files>='I<files>'

The space-separated list of release files produced.  Does not include
the metadata file itself.

=item B<source_repo>='I<URL>'

The URL of the source repository that this release was generated from.

=back

=back

=head1 COPYRIGHT

Copyright 2020-2023 The OpenSSL Project Authors. All Rights Reserved.

Licensed under the Apache License 2.0 (the "License").  You may not use
this file except in compliance with the License.  You can obtain a copy
in the file LICENSE in the source distribution or at
L<https://www.openssl.org/source/license.html>.

=cut
### END MANUAL
EOF

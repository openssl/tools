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
                Implies --branch.

--branch        Create a release branch 'openssl-{major}.{minor}',
                where '{major}' and '{minor}' are the major and minor
                version numbers.

--clean-worktree
                Expect the current worktree to be clean, and uses it directly.
                This implies the current branch of the worktree will be updated.

--branch-fmt=<fmt>
                Format for branch names.
                Default is "%b" for the release branch.
--tag-fmt=<fmt> Format for tag names.
                Default is "%t" for the release tag.

--reviewer=<id> The reviewer of the commits.
--local-user=<keyid>
                For the purpose of signing tags and tar files, use this
                key (default: use the default e-mail address’ key).
--unsigned      Do not sign anything.

--staging-address=<address>
                The staging location to upload release files to (default:
                upload@dev.openssl.org)
--no-upload     Don't upload the staging release files.
--no-update     Don't perform 'make update' and 'make update-fips-checksums'.
--quiet         Really quiet, only the final output will still be output.
--verbose       Verbose output.
--debug         Include debug output.  Implies --no-upload.
--porcelain     Give the output in an easy-to-parse format for scripts.

--force         Force execution

--help          This text
--manual        The manual

If none of --alpha, --beta, or --final are given, this script tries to
figure out the next step.
EOF
    exit 0
}

# Set to one of 'major', 'minor', 'alpha', 'beta' or 'final'
next_method=
next_method2=

do_branch=false
warn_branch=false

do_upload=true
do_update=true

clean_worktree=false

default_branch_fmt='OSSL--%b--%v'
default_tag_fmt='%t'

ECHO=echo
DEBUG=:
VERBOSE=:
git_quiet=-q
do_porcelain=false

force=false

do_help=false
do_manual=false

do_signed=true
tagkey=' -s'
gpgkey=
reviewers=

staging_address=upload@dev.openssl.org

TEMP=$(getopt -l 'alpha,next-beta,beta,final' \
              -l 'branch' \
              -l 'clean-worktree' \
              -l 'branch-fmt:,tag-fmt:' \
              -l 'reviewer:' \
              -l 'local-user:,unsigned' \
              -l 'staging-address:' \
              -l 'no-upload,no-update' \
              -l 'quiet,verbose,debug' \
              -l 'porcelain' \
              -l 'force' \
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
        if [ "$next_method" = 'final' ]; then
            do_branch=true
        fi
        ;;
    --next-beta )
        next_method2=$(echo "x$1" | sed -e 's|^x--next-||')
        shift
        ;;
    --branch )
        do_branch=true
        warn_branch=true
        shift
        ;;
    --clean-worktree )
        clean_worktree=true
        default_branch_fmt='%b'
        default_tag_fmt='%t'
        shift
        ;;
    --branch-fmt )
        shift
        branch_fmt="$1"
        shift
        ;;
    --tag-fmt )
        shift
        tag_fmt="$1"
        shift
        ;;
    --reviewer )
        reviewers="$reviewers $1=$2"
        shift
        shift
        ;;
    --local-user )
        shift
        do_signed=true
        tagkey=" -u $1"
        gpgkey=" -u $1"
        shift
        ;;
    --unsigned )
        shift
        do_signed=false
        tagkey=" -a"
        gpgkey=
        ;;
    --staging-address )
        shift
        staging_address="$1"
        shift
        ;;
    --no-upload )
        do_upload=false
        shift
        ;;
    --no-update )
        do_update=false
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
        do_upload=false
        shift
        ;;
    --porcelain )
        do_porcelain=true
        shift
        ;;
    --force )
        force=true
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

if [ -z "$branch_fmt" ]; then branch_fmt="$default_branch_fmt"; fi
if [ -z "$tag_fmt" ]; then tag_fmt="$default_tag_fmt"; fi

$DEBUG >&2 "DEBUG: \$next_method=$next_method"
$DEBUG >&2 "DEBUG: \$next_method2=$next_method2"

$DEBUG >&2 "DEBUG: \$do_branch=$do_branch"

$DEBUG >&2 "DEBUG: \$do_upload=$do_upload"
$DEBUG >&2 "DEBUG: \$do_update=$do_update"
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
          "$RELEASE_AUX/release-data-fn.sh" \
          "$RELEASE_AUX/string-fn.sh" \
          "$RELEASE_AUX/upload-fn.sh"; do
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
# Load string manipulation functions
. $RELEASE_AUX/string-fn.sh
# Load upload backend functions
. $RELEASE_AUX/upload-fn.sh

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
elif $force; then
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

# We turn staging_address into a few variables, which can be used
# by backends that must understand a subset of the SFTP commands
staging_directory=
staging_backend=
case "$staging_address" in
    *:* )
        # Something with a colon is interpreted as the typical SCP
        # location.  We reinterpret that in our terms
        staging_directory="${staging_address#*:}"
        staging_address="${staging_address%%:*}"
        staging_backend=sftp
        ;;
    *@* )
        staging_backend=sftp
        ;;
    sftp://?*/* | sftp://?* )
        # First, remove the URI scheme
        staging_address="${staging_address#sftp://}"
        # Now we know that we have a host, followed by a slash, followed by
        # a directory spec.  If there is no slash, there's no directory.
        staging_directory="${staging_address#*/}"
        if [ "$staging_directory" = "$staging_address" ]; then
            # There was nothing with a slash to remove, so no directory.
            staging_directory=
        fi
        staging_address="${staging_address%%/*}"
        staging_backend=sftp
        ;;
    sftp:* )
        echo >&2 "Invalid staging address $staging_address"
        exit 1
        ;;
    * )
        if $do_upload && ! [ -d "$staging_address" ]; then
           echo >&2 "Not an existing directory: $staging_address"
           exit 1
        fi
        staging_backend=file
        ;;
esac

# Initialize #########################################################

$ECHO "== Initializing work tree"

release_clone=
if $clean_worktree; then
    if [ -n "$(git status -s)" ]; then
        echo >&2 "You've specified --clean-worktree, but your worktree is unclean"
        exit 1
    fi
else
    # Generate a cloned directory name
    release_clone="$orig_branch-release-tmp"

    $ECHO "== Work tree will be in $release_clone"

    # Make a clone in a subdirectory and move there
    if ! [ -d "$release_clone" ]; then
        $VERBOSE "== Cloning to $release_clone"
        git clone $git_quiet -b "$orig_branch" -o parent . "$release_clone"
    fi
    cd "$release_clone"
fi

get_version

# Branches to start from.  The release branch is where the changes for the
# release are made, and the update branch is where the post-release changes are
# made.  If --branch was given and is relevant, they should be different (and
# the update branch should be 'master'), otherwise they should be the same.
orig_update_branch="$orig_branch"
orig_release_branch="$(std_branch_name)"

# among others, we only create a release branch if the patch number is zero
if [ "$orig_update_branch" = "$orig_release_branch" ] \
       || [ -n "$PATCH" -a "$PATCH" != 0 ]; then
    if $do_branch && $warn_branch; then
        echo >&2 "Warning! We're already in a release branch; --branch ignored"
    fi
    do_branch=false
fi

if $do_branch; then
    if [ "$orig_update_branch" != "master" ]; then
        echo >&2 "--branch is invalid unless the current branch is 'master'"
        exit 1
    fi
    # No need to check if $orig_update_branch and $orig_release_branch differ,
    # 'cause the code a few lines up guarantee that if they are the same,
    # $do_branch becomes false
else
    # In this case, the computed release branch may differ from the update branch,
    # even if it shouldn't...  this is the case when alpha or beta releases are
    # made in the master branch, which is perfectly ok.  Therefore, simply reset
    # the release branch to be the same as the update branch and carry on.
    orig_release_branch="$orig_update_branch"
fi

# Check that the current branch is still on the same branch as our parent repo,
# or on a release branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" = "$orig_update_branch" ]; then
    :
elif [ "$current_branch" = "$orig_release_branch" ]; then
    :
else
    # It is an error to end up here.  Let's try to figure out what went wrong

    if $clean_worktree; then
        # We should never get here.  If we do, something is incorrect in
        # the code above.
        echo >&2 "Unexpected current branch: $current_branch"
    else
        echo >&2 "The cloned sub-directory '$release_clone' is on a branch"
        if [ "$orig_update_branch" = "$orig_release_branch" ]; then
            echo >&2 "other than '$orig_update_branch'."
        else
            echo >&2 "other than '$orig_update_branch' or '$orig_release_branch'."
        fi
        echo >&2 "Please 'cd \"$(pwd)\"; git checkout $orig_update_branch'"
    fi
    exit 1
fi

SOURCEDIR=$(pwd)
$DEBUG >&2 "DEBUG: Source directory is $SOURCEDIR"

# Release ############################################################

# We always expect to start from a state of development
if [ "$TYPE" != 'dev' ]; then
    if $clean_worktree; then
        cat >&2 <<EOF
Not in a development branch.

Have a look at the git log, it may be that a previous crash left it in
an intermediate state and that need to drop the top commit:

git reset --hard $orig_head
# WARNING! LOOK BEFORE YOU ACT, KNOW WHAT YOU DO
EOF
    else
        cat >&2 <<EOF
Not in a development branch.

Have a look at the git log in $release_clone, it may be that
a previous crash left it in an intermediate state and that need to drop
the top commit:

(cd $release_clone; git reset --hard $upstream)
# WARNING! LOOK BEFORE YOU ACT, KNOW WHAT YOU DO
EOF
    fi
    exit 1
fi

# Update the version information.  This won't save anything anywhere, yet,
# but does check for possible next_method errors before we do bigger work.
next_release_state "$next_method"

# Make the update branch name according to our current data
update_branch=$(format_string "$branch_fmt" \
                              "b=$orig_update_branch" \
                              "t=" \
                              "v=$FULL_VERSION")
    
# Make the release tag and branch name according to our current data
release_tag=$(format_string "$tag_fmt" \
                            "b=$orig_release_branch" \
                            "t=$(std_tag_name)" \
                            "v=$FULL_VERSION")
release_branch=$(format_string "$branch_fmt" \
                               "b=$orig_release_branch" \
                               "t=$(std_tag_name)" \
                               "v=$FULL_VERSION")
    
# Create a update branch, unless it's the same as our current branch
if [ "$update_branch" != "$orig_update_branch" ]; then
    $VERBOSE "== Creating a local update branch and switch to it: $update_branch"
    git checkout $git_quiet -b "$update_branch"
fi

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
    announce_template=openssl-announce-pre-release.tmpl
else
    release_type=$(std_release_type $VERSION)
    release_text="$release"
    announce_template=openssl-announce-release-$release_type.tmpl
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
$ECHO "Tagging release with tag $release_tag.  You may need to enter a pass phrase"
git tag$tagkey "$release_tag" -m "OpenSSL $release release tag"

tarfile=openssl-$release.tar
tgzfile=$tarfile.gz
metadata=openssl-$release.dat
announce=openssl-$release.txt

$ECHO "== Generating tar, hash, announcement and metadata files."
$ECHO "== This make take a bit of time..."

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
echo $sha1hash "$tgzfile" > "../$tgzfile.sha1"
sha256hash=$(openssl sha256 < "../$tgzfile" | \
    (IFS='= '; while read X H; do echo $H; done))
echo $sha256hash "$tgzfile" > "../$tgzfile.sha256"
length=$(wc -c < "../$tgzfile")

$VERBOSE "== Generating announcement text: $announce"
# Hack the announcement template
cat "$RELEASE_AUX/$announce_template" \
    | sed -e "s|\\\$release_text|$release_text|g" \
          -e "s|\\\$release_tag|$release_tag|g" \
          -e "s|\\\$release|$release|g" \
          -e "s|\\\$series|$SERIES|g" \
          -e "s|\\\$label|$PRE_LABEL|g" \
          -e "s|\\\$tarfile|$tgzfile|" \
          -e "s|\\\$length|$length|" \
          -e "s|\\\$sha1hash|$sha1hash|" \
          -e "s|\\\$sha256hash|$sha256hash|" \
    | perl -p "$RELEASE_AUX/fix-title.pl" \
    > "../$announce"

$VERBOSE "== Generating signatures: $tgzfile.asc $announce.asc"
rm -f "../$tgzfile.asc" "../$announce.asc"
$ECHO "Signing the release files.  You may need to enter a pass phrase"
if $do_signed; then
    gpg$gpgkey --use-agent -sba "../$tgzfile"
    gpg$gpgkey --use-agent -sta --clearsign "../$announce"
fi

if ! $clean_worktree; then
    # Push everything to the parent repo
    $VERBOSE "== Push what we have to the parent repository"
    git push --follow-tags parent HEAD
fi

if $do_signed; then
    staging_files=( "$tgzfile" "$tgzfile.sha1" "$tgzfile.sha256"
                    "$tgzfile.asc" "$announce.asc" )
else
    staging_files=( "$tgzfile" "$tgzfile.sha1" "$tgzfile.sha256" "$announce" )
fi

$VERBOSE "== Generating metadata file: $metadata"

(
    set -x
    if [ "$update_branch" != "$orig_update_branch" ]; then
        echo "staging_update_branch='$update_branch'"
    fi
    echo "update_branch='$orig_update_branch'"
    if [ "$release_branch" != "$update_branch" ]; then
        if [ "$release_branch" != "$orig_release_branch" ]; then
            echo "staging_release_branch='$release_branch'"
        fi
        echo "release_branch='$orig_release_branch'"
    fi
    echo "release_tag='$release_tag'"
    echo "upload_files='${staging_files[@]}'"
    echo "source_repo='$orig_remote_url'"
) > ../$metadata

if $do_upload; then
    $ECHO "== Upload tar, hash, announcement and metadata files to staging location"
fi

(
    # With sftp, the progress meter is enabled by default,
    # so we turn it off unless --verbose was given
    if [ "$VERBOSE" == ':' ]; then
        echo "progress"
    fi
    if [ -n "$staging_directory" ]; then
        echo "cd $staging_directory"
    fi
    for uf in "${staging_files[@]}" "$metadata"; do
        echo "put ../$uf"
    done
) | upload_backend_$staging_backend "$staging_address" $do_upload

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

if ! $clean_worktree; then
    # Push everything to the parent repo
    $VERBOSE "== Push what we have to the parent repository"
    git push parent HEAD
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

if ! $clean_worktree; then
    # Push everything to the parent repo
    $VERBOSE "== Push what we have to the parent repository"
    git push parent HEAD
fi

# Done ###############################################################

$VERBOSE "== Done"

cd $HERE
if $do_porcelain; then
    if [ -n "$release_clone" ]; then
        echo "clone_directory='$release_clone'"
    fi
    echo "orig_head='$orig_head'"
    echo "metadata='$metadata'"
else
    cat <<EOF

======================================================================
The release is done, and involves a few files and commits for you to
deal with.  Everything you need has been pushed to your repository,
please see instructions that follow.
======================================================================

EOF

    if $do_upload; then
        cat <<EOF
The following files were uploaded to $staging_address, please ensure they
are dealt with appropriately:

EOF
    else
        cat <<EOF
The following files were generated for upload, please deal with them
appropriately:

EOF
    fi
    for uf in "${staging_files[@]}"; do
        echo "    $uf"
    done
    cat <<EOF

----------------------------------------------------------------------

EOF

    if [ "$release_branch" != "$update_branch" ]; then
        cat <<EOF
You need to prepare the main repository with a new branch, '$release_branch'.
That is done directly in the server's bare repository like this:

    git branch $release_branch $orig_HEAD

EOF
    fi
    if [ "$update_branch" != "$orig_update_branch" ] \
       && [ "$release_branch" != "$update_branch" ]; then
        # "Normal" scenario with --branch
        cat <<EOF
A release tag and two branches have been added to your local repository.
Push them to github, make PRs from them and have them approved.

    Update branch: $update_branch
    Release branch: $release_branch
    Tag: $release_tag

When merging everything into the main repository, do it like this:

    git push git@github.openssl.org:openssl/openssl.git \\
        $release_branch:$orig_release_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $update_branch:$orig_update_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $release_tag
EOF
    elif [ "$update_branch" != "$orig_update_branch" ]; then
        # "Normal" scenario without --branch
        cat <<EOF
A release tag and a release/update branch have been added to your local
repository.  Push them to github, make PRs from them and have them
approved.

    Release/update branch: $update_branch
    Tag: $release_tag

When merging everything into the main repository, do it like this:

    git push git@github.openssl.org:openssl/openssl.git \\
        $update_branch:$orig_update_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $release_tag
EOF
    elif [ "$release_branch" != "$update_branch" ]; then
        # --clean-worktree and --branch scenario
        cat <<EOF
A release tag and a release branch has been added to your repository,
and the current branch has been updated.  Push them to github, make
PRs from them and have them approved:

    Updated branch: $update_branch
    Release branch: $release_branch
    Tag: $release_tag

When merging everything into the main repository, do it like this:

    git push git@github.openssl.org:openssl/openssl.git \\
        $release_branch:$orig_release_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $update_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $release_tag
EOF
    else
        # --clean-worktree without --branch scenario
        cat <<EOF
A release tag has been added to your local repository, and the current
branch has been updated.  Push them to github, make PRs from them and
have them approved.

    Release/update branch: $update_branch
    Tag: $release_tag

When merging everything into the main repository, do it like this:

    git push git@github.openssl.org:openssl/openssl.git \\
        $update_branch
    git push git@github.openssl.org:openssl/openssl.git \\
        $release_tag
EOF
    fi

    cat <<EOF

----------------------------------------------------------------------
EOF

    cat <<EOF

When everything is done, or if something went wrong and you want to start
over, simply clean away temporary things left behind:
EOF
    if [ -n "$release_clone" ]; then
        cat <<EOF
The release worktree:

    rm -rf $release_clone
EOF
    fi
    cat <<EOF

Additional branches:

EOF
    if [ "$release_branch" != "$update_branch" ]; then
        cat <<EOF
    git branch -D $release_branch
EOF
    fi
    if [ "$update_branch" != "$orig_update_branch" ]; then
        cat <<EOF
    git branch -D $update_branch
EOF
    fi
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
B<--branch> |
B<--clean-worktree> |
B<--branch-fmt>=I<fmt> |
B<--tag-fmt>=I<fmt> |
B<--local-user>=I<keyid> |
B<--unsigned> |
B<--reviewer>=I<id> |
B<--staging-address>=I<address> |
B<--no-upload> |
B<--no-update> |
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

B<stage-release.sh> normally leaves behind a clone of the local repository,
as a subdirectory in the current worktree, as well as an extra branch with
the results of running this script in the local repository.  This extra
branch is useful to create a pull request from, which will also be mentioned
at the end of the run of B<stage-release.sh>.  This local clone subdirectory
as well as this extra branch can safely be removed after all instructions
have been successfully followed.

When the option B<--clean-worktree> is given, B<stage-release.sh> has a
different behaviour.  In this case, it doesn't create that clone or any
extra branch, and it will update the current branch of the worktree
directly.  This is useful when it's desirable to push the changes directly
to a remote repository without having to go through a pull request and
approval process.

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

This implies B<--branch>.

=item B<--branch>

Create a branch specific for the I<SERIES> release series, if it doesn't
already exist, and switch to it when making the release files.  The exact
branch name will be C<< openssl-I<SERIES> >>.

=item B<--clean-worktree>

This indicates that the current worktree is clean and can be acted on
directly, instead of creating a clone of the local repository or creating
any extra branch.

=item B<--branch-fmt>=I<fmt>

=item B<--tag-fmt>=I<fmt>

Format for branch and tag names.  This can be used to tune the names of
branches and tags that are updated or added by this script.

I<fmt> can include printf-like formating directives:

=over 4

=item %b

is replaced with a branch name.  This branch name is usually the current
branch of the current repository, but may also be the default release
branch name that is generated when B<--branch> is given.

=item %t

is replaced with the generated release tag name.

=item %v

is replaced with the version number.  The exact version number varies
through the process of this script.

=back

This script uses the following defaults:

=over 4

=item * Without B<--clean-worktree>

For branches: C<OSSL--%b--%v>

For tags: C<%t>

=item * With B<--clean-worktree>

For branches: C<%b>

For tags: C<%t>

=back

=item B<--reviewer>=I<id>

Add I<id> to the set of reviewers for the commits performed by this script.
Multiple reviewers are allowed.

If no reviewer is given, you will have to run C<addrev> manually, which
means retagging a release commit manually as well.

=item B<--local-user>=I<keyid>

Use I<keyid> as the local user for C<git tag> and for signing with C<gpg>.

If not given, then the default e-mail address' key is used.

=item B<--unsigned>

Do not sign the tarball or announcement file.  This leaves it for other
scripts to sign the files later.

=item B<--staging-address>=I<address>

The staging location that the release files are to be uploaded to.
Supported values are:

=over 4

=item -

an existing local directory

=item -

something that can be interpreted as an SCP/SFTP address.  In this case,
SFTP will always be used.  Typical SCP remote file specs will be translated
into something that makes sense for SFTP.

=back

The default staging address is C<upload@dev.openssl.org>.

=item B<--no-upload>

Don't upload the release files to the staging location.

=item B<--no-update>

Don't run C<make update> and C<make update-fips-checksums>.

=item B<--quiet>

Really quiet, only bare necessity output, which is the final instructions,
or should the B<--porcelain> option be used, only that output.

messages appearing on standard error will still be shown, but should be
fairly minimal.

=item B<--verbose>

Verbose output.

=item B<--debug>

Display extra debug output.  Implies B<--no-upload>

=item B<--porcelain>

Give final output in an easy-to-parse format for scripts.  The output comes
in a form reminicent of shell variable assignments.  Currently supported are:

=over 4

=item B<clone_directory>=I<dir>

The directory for the clone that this script creates.  This is not given when
the option B<--clean-worktree> is used.

=item B<metadata>=I<file>

The metadata file.  See L</FILES> for a description of all generated files
as well as the contents of the metadata file.

=back

=item B<--force>

Force execution.  Precisely, the check that the current branch is C<master>
or a release branch is not done.

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

The following files are produced and normally uploaded to the staging
address:

=over 4

=item F<openssl-{VERSION}.tar.gz>

The source tarball itself.

=item F<openssl-{VERSION}.tar.gz.sha1>, F<openssl-{VERSION}.tar.gz.sha256>

The SHA1 and SHA256 checksums for F<openssl-{VERSION}.tar.gz>.

=item F<openssl-{VERSION}.tar.gz.asc>

The detached PGP signature for F<openssl-{VERSION}.tar.gz>.

=item F<openssl-{VERSION}.txt.asc>

The announcement text, clear signed with PGP.

=item F<openssl-{VERSION}.dat>

The metadata file for F<openssl-{VERSION}.tar.gz>.  It contains shell
variable assignments with data that may be of interest for other scripts,
such as a script to promote this release to an actual release:

=over 4

=item B<update_branch>=I<branch>

The update branch.  This is always given.

=item B<staging_update_branch>=I<branch>

If a staging update branch was used (because B<--clean-worktree> wasn't
given or because B<--branch-fmt> was used), it's given here.

=item B<release_branch>=I<branch>

The release branch, if it differs from the update branch (i.e. B<--branch>
was given or implied).

=item B<staging_release_branch>=I<branch>

If a staging release branch was used (because B<--clean-worktree> wasn't
given or because B<--branch-fmt> was used), it's given here.

=item B<release_tag>=I<tag>

The release tag.  This is always given.

=item B<upload_files>='I<files>'

The space separated list of files that were or would have been uploaded
to the staging location (depending on the presence of B<--no-upload>).  This
list doesn't include the metadata file itself.

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

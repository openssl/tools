#! /bin/bash -e
# Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# Force C locale because some commands (like date +%b) relies
# on the current locale.
export LC_ALL=C

usage () {
    cat <<EOF
Usage: publish-release.sh [ options ... ]

EOF
    exit 0
}

# The staging repository is determined by the staging type, unless given
# explicitly by command line options
declare -A staging_repositories=(
    [public]=${PUBLIC_STAGING_REPOSITORY:-'git@github.openssl.org:openssl/staging.git'}
    [premium]=${PREMIUM_STAGING_REPOSITORY:-'git@github.openssl.org:openssl/staging.git'}
    [security]=${SECURITY_STAGING_REPOSITORY:-'git@github.openssl.org:openssl/staging-security.git'}
)

# Public or premium release?  Let the version numbers determine it!
declare -A release_types=(
    [premium]='^1\.0\.2'
    [public]='^(1\.1\.1|[3-9]\.)'
)

# The upload location and gh release repository is determined by the version
# of the release that's being prepared, unless given explicitly by command
# line options
declare -A upload_locations=(
    [public]=${PUBLIC_RELEASE_LOCATION:-/srv/ftp/source}
)
declare -A gh_release_repositories=(
    [public]=${PUBLIC_RELEASE_REPOSITORY:-github.com/openssl/openssl}
    [premium]=${PREMIUM_RELEASE_REPOSITORY:-github.openssl.org/openssl/extended-releases}
)

# The staging type can be one of 'public', 'premium', 'security' and
# 'custom'
# All except 'custom' have pre-determined locations and repositories (which
# can be modified by command line options).  With the 'custom' staging type,
# all hands are off, and all locations and repositories MUST be given on the
# command line

staging_type=public
staging_repository=
staging_location=${STAGING_LOCATION:-/sftp/upload/incoming}
upload_location=
gh_release_repository=
data_repository=${DATA_REPOSITORY:-git@github.openssl.org:omc/data.git}
email=
do_all_versions=false
do_versions=()
do_file_upload=true
do_gh_upload=true
do_update=true
do_mail=true
gpg_key=
tag_key=' -s'

ECHO=echo
DEBUG=:
VERBOSE=:
git_quiet=-q

TEMP=$(getopt -l 'all,version:' \
              -l 'staging-location:,staging-repository:' \
              -l 'upload-location:,gh-release-repository:' \
              -l 'data-repository:' \
              -l 'public,premium,security,custom' \
              -l 'email:,reviewer:' \
              -l 'no-file-upload,no-gh-upload,no-upload,no-update,no-mail' \
              -l 'quiet,verbose,debug' \
              -l 'help,manual' \
              -n publish-release.sh -- - "$@")
eval set -- "$TEMP"
while true; do
    case $1 in
        --all )
            do_all_versions=true
            shift
            ;;
        --version )
            do_versions+=($2)
            shift
            shift
            ;;
        --staging-location )
            shift
            staging_location=$1
            shift
            ;;
        --staging-repository )
            staging_repository=$(realpath $2)
            shift
            shift
            ;;
        --upload-location )
            upload_location=$(realpath $2)
            shift
            shift
            ;;
        --gh-release-repository )
            gh_release_repository=$2
            shift
            shift
            ;;
        --data-repository )
            data_repository=$2
            shift
            shift
            ;;
        --public | --premium | --security | --custom )
           staging_type=${1#--}
           shift
           ;;
        --email )
            email=$2
            gpg_key=" -u $email"
            tag_key=" -u $email"
            shift
            shift
            ;;
        --reviewer )
            reviewers+=" $1=$2"
            shift
            shift
            ;;
        --no-file-upload )
            do_file_upload=false
            shift
            ;;
        --no-gh-upload )
            do_gh_upload=false
            shift
            ;;
        --no-upload )
            do_file_upload=false
            do_gh_upload=false
            shift
            ;;
        --no-update )
            do_update=false
            shift
            ;;
        --no-mail )
            do_mail=false
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
        * )
            echo >&2 "Unknown option $1"
            exit 1
            ;;
    esac
done

# Checks #############################################################

check_messages=()

missing_commands=()
# There are certain commands that we use
for c in git gh mutt gpg; do
    if ! (command -v $c > /dev/null 2>&1); then
        missing_commands+=($c)
    fi
done
if [[ ${#missing_commands[@]} > 0 ]]; then
    check_messages+=( "Missing commands: ${missing_commands[@]}" )
fi

# The --email argument must be a valid OpenSSL email address.  We only check
# that loosly, though, by ensuring that the proper host part is used
if [[ "$email" != *"@openssl.org" ]]; then
    check_messages+=( "--email argument isn't a proper OpenSSL email address: $email" )
fi

# There must also be a PGP key tied to the email address
if ! gpg -K -u $email >/dev/null 2>&1; then
    check_messages+=( "There is no private key for $email present" )
fi

if [ "$staging_type" = "custom" ]; then
    if [ -z "$staging_location" ]; then
        check_messages+=( "You MUST specify a release file staging location with --staging-location" )
    fi
    if [ -z "$staging_repository" ]; then
        check_messages+=( "You MUST specify a staging repository with --staging-repository" )
    fi
    # $upload_location and $gh_release_repository may still be empty
fi

if [ -n "$staging_repository" ]; then
    srs=( "$staging_repository" )
else
    srs=( "${staging_repositories[@]}" )
fi
for sr in "${srs[@]}"; do
    if [ -z "$(git ls-remote "$sr" 2>/dev/null)" ]; then
        check_messages+=( "Can't access the staging repository '$sr'" )
    fi
done

if [ -n "$data_repository" ]; then
    if [ -z "$(git ls-remote "$data_repository" 2>/dev/null)" ]; then
        check_messages+=( "Can't access the data repository '$data_repository'" )
    fi
fi

if $do_file_upload; then
    if [ -n "$upload_location" ]; then
        uls=( "$upload_location" )
    else
        uls=( "${upload_locations[@]}" )
    fi
    for ul in "${uls[@]}"; do
        if ! [ -d "$ul" ]; then
            check_messages+=( "Can't access the upload location '$ul'" )
        fi
    done
fi

if $do_gh_upload; then
    if [ -n "$gh_release_repository" ]; then
        grrs=( "$gh_release_repository" )
    else
        grrs=( "${gh_release_repositories[@]}" )
    fi
    for grr in "${grrs[@]}"; do
        h=${grr%%/*}
        if ! gh auth status -h "$h" >/dev/null 2>&1; then
            check_messages+=( "You're not authenticated to interact with $h using 'gh'" )
        fi
    done
fi

if [[ ${#check_messages[@]} > 0 ]]; then
    for m in "${check_messages[@]}"; do
        echo >&2 "$m"
    done
    exit 1
fi

# Setup ##############################################################

$ECHO "== Initializing temporary work directory"

# Create a temporary work directory where everything happens
workdir=$(mktemp -d -p /var/tmp)
cd "$workdir"

$VERBOSE "-- Temporary work directory is $workdir"

# Verbosity feed for certain commands
VERBOSITY_FIFO=/tmp/openssl-$$.fifo
mkfifo -m 600 $VERBOSITY_FIFO
( cat $VERBOSITY_FIFO | while read L; do $VERBOSE "> $L"; done ) &
exec 42>$VERBOSITY_FIFO

# Cleanup trap
trap "exec 42>&-; rm $VERBOSITY_FIFO; rm -rf '$workdir'" 0 2

# The staging repository is determined by the staging type, so will
# always be the same for all releases prepared in a run of this script
if [ -z "$staging_repository" ]; then
    staging_repository="${staging_repositories[$staging_type]}"
fi
if ! [ -n "$staging_repository" ]; then
    echo >&2 "Assertion: '[ -n \"$staging_repository\" ]' failed"
    exit 2
fi

# Collect files to look at (and do a version check) ##################

$ECHO "== Collecting staged release data files"

data_files=()
if $do_all_versions; then
    for d in "$staging_location"/openssl-*.dat; do
        data_files+=( "$(basename $d)" )
    done
else
    missing_versions=""
    for v in "${do_versions[@]}"; do
        data_file="openssl-$v.dat"
        data_files+=( "$data_file" )
        if ! [ -f "$staging_location/$data_file" ]; then
            if [ -n "$missing_versions" ]; then
                missing_versions+=", $v"
            else
                missing_versions=$v
            fi
        fi
    done
    if [ -n "$missing_versions" ]; then
        echo >&2 "The following OpenSSL versions haven't been staged:"
        echo >&2 "  $missing_versions"
        echo >&2 "Skipping..."
    fi
fi

$VERBOSE "-- Data files found in ${staging_location}:"
for d in "${data_files[@]}"; do
    $VERBOSE "--   $d"
done

# Clone common repositories ##########################################

$ECHO "== Cloning necessary git repositories (data and staging)"

git clone $git_quiet $data_repository data
git clone $git_quiet --bare $staging_repository staging

# Process each data file #############################################

for d in "${data_files[@]}"; do
    $ECHO "== Processing staged release data $d"

    (
        ##############################################################
        #
        #  Check and prepare the release
        #
        #####

        # Suck in all variables from the data file.
        # Expected variables:
        #
        # source_repo, update_branch, release_tag, upload_files
        . "$staging_location"/"$d"

        # Verify that what we got makes sense (at least exists)
        if [ -z "$release_tag" -o -z "$upload_files" \
          -o -z "$update_branch" -o -z "$source_repo" \
          -o -z "$release_version" -o -z "$release_series" \
          -o -z "$release_full_version" -o -z "$release_text" ]; then
            echo >&2 "Warning: $d doesn't contain what we expect.  Skipping..."
            # exit 0 to not break the outer loop
            exit 0
        fi
        # ... including that the release tag exists in the staging repo
        if ! ( cd staging; git rev-parse $git_quiet --verify $release_tag ); then
            echo >&2 "Warning: $release_tag does not exist in $staging_repository.  Skipping..."
            echo >&2 "(this is probably due to using the wrong staging type)"
            exit 0
        fi

        # Separate release branches (i.e. the --branch option in stage-release.sh)
        # are unsupported, because running addrev causes history rewrite, which
        # means the merge point between the update branch and the release branch
        # has to move, which we don't know how to do safely.
        if [ -n "$release_branch" ]; then
            echo >&2 "Warning: the release of $release_version includes a release branch"
            echo >&2 "  This is unsupported and requires human intervention"
            exit 0
        fi

        # Determine the release type and associated variables from version
        # numbers, unless the staging type is 'custom'
        if [ "$staging_type" != "custom" ]; then
            for rt in "${!release_types[@]}"; do
                re="${release_types[$rt]}"
                if [[ "$release_version" =~ $re ]]; then
                    release_type=$rt
                    break
                fi
            done
            if [ -z "$release_type" ]; then
                echo >&2 "Warning: OpenSSL $version is staged, but is not supported for release.  Skipping..."
                exit 0
            fi

            # Determine the upload location and gh release repository
            # (we're in a subprocess, so it's safe to assign these variables
            # here, as those assignments these will be lost when the next
            # release is to be processed)
            if [ -z "$upload_location" ]; then
                upload_location="${upload_locations[$release_type]}"
            fi
            if [ -z "$upload_location" ]; then
                gh_release_repository="${gh_release_repositories[$release_type]}"
            fi
        fi

        # The source repo is going to get massaged, let's make sure to save
        # the original
        orig_source_repo=$source_repo

        # If the source repository is on github.com, we know that
        # the repository to push to is really on github.openssl.org.
        source_repo=${source_repo/github.com/github.openssl.org}

        # If the source repository is presented as https://, we know
        # how to convert it to git+ssh format.
        source_repo=${source_repo/#https:\/\/github.openssl.org\//git@github.openssl.org:}

        # Now that we know what branch we're dealing with, update the
        # checked out staging repo, and add / update a remote for the
        # source repo.
        source_remote_name=$(basename "$source_repo" .git)
        (
            cd staging
            if ! git -q remote get-url $source_remote_name >/dev/null 2>&1; then
                git remote add $source_remote_name $source_repo
            fi
            git fetch $git_quiet $source_remote_name
        )

        # Create a newsflash line from the full version info
        v=${release_full_version%%+*} # version without build metadata
        t=${v#*-}                     # The pre-release tag
        if [[ "$t" == '-alpha'* ]]; then
            newsflash="Alpha ${t#-alpha} of OpenSSL $release_series is now available: please download and test it"
        elif [[ "$t" == '-beta'* ]]; then
            newsflash="Beta ${t#-beta} of OpenSSL $release_series is now available. This is a release candidate: please download and test it"
        elif [[ "$version" == *.0 ]]; then
            newsflash="Final version of OpenSSL $release_version is now available: please download and upgrade!"
        else
            if [[ "$staging_type" == "security" ]]; then
                newsflash="OpenSSL $release_version is now available, including bug and security fixes"
            else
                newsflash="OpenSSL $release_version is now available, including bug fixes"
            fi
        fi

        ##############################################################
        #
        #  Fixups
        #
        #####

        $ECHO "-- Adding reviewer records for: $reviewers"

        ub=$update_branch
        if [ -n "$staging_update_branch" ]; then
            ub=${staging_update_branch}
        fi
        (
            cd staging
            $DEBUG >&2 "DEBUG: Running addrev on $source_remote_name/$update_branch..$ub"
            DATA=$(realpath ../data) addrev --nopr $reviewers \
                $source_remote_name/$update_branch..$ub
        )

        # - [TEMPORARY] Some of the staged release files are expected to be
        #   unsigned, or to be signed with a key that isn't suitable for
        #   publishing, because the signer isn't specified in OpenSSL's
        #   doc/fingerprints.txt.
        #   Therefore, they must be signed (possibly resigned) now.
        # - [TEMPORARY] The staging repository has a tag that's expected to
        #   be unsigned or to be signed with a key that isn't suitable for
        #   publishing, because the signer isn't specified in OpenSSL's
        #   doc/fingerprints.txt.
        #   Therefore, that tag must be signed (possibly resigned) now.
        #
        # These fixups will be removed when we have fully moved to using a
        # team key for signing the releases.

        $ECHO "-- (Re-)signing release files and release tag"
        $ECHO "-- You may be asked for your GPG key passphrase"

        new_upload_files=()
        for f in $upload_files; do
            if [[ "$f" == *.tar.gz ]]; then
                # Found the tarball.  Sign it!
                $VERBOSE "--   (Re-)signing $staging_location/$f"
                gpg --yes --pinentry-mode loopback $gpg_key \
                    -o "$staging_location"/"$f.asc" \
                    -sba "$staging_location"/"$f"
                new_upload_files+=("$staging_location"/"$f"
                                   "$staging_location"/"$f.asc")
            elif [[ "$f" == *.txt.asc ]]; then
                # Found the announcement text, already signed.  Re-sign it!
                ff=$(basename "$f" .asc)
                $VERBOSE "--   (Re-)signing $staging_location/$ff"
                # Extract the unsigned text
                gpg --yes --pinentry-mode loopback $gpg_key \
                    -o "$staging_location"/"$ff" \
                    "$staging_location"/"$f"
                # ... then sign it
                gpg --yes --pinentry-mode loopback $gpg_key \
                    -o "$staging_location"/"$f" \
                    -sta --clearsign "$staging_location"/"$ff"
                new_upload_files+=("$staging_location"/"$f")
            elif [[ "$f" == *.txt ]]; then
                # Found the announcement text.  Sign it!
                $VERBOSE "--   (Re-)signing $staging_location/$f"
                gpg --yes --pinentry-mode loopback $gpg_key \
                    -o "$staging_location"/"$f.asc" \
                    -sta --clearsign "$staging_location"/"$f"
                new_upload_files+=("$staging_location"/"$f.asc")
            else
                new_upload_files+=("$staging_location"/"$f")
            fi
        done

        (
            $VERBOSE "--   (Re-)signing the release tag $release_tag"
            cd staging
            m="$( git cat-file -p $release_tag \
                      | sed -e '1,/^ *$/d' \
                            -e '/^-----BEGIN PGP SIGNATURE-----$/,$d' )"
            git tag$tag_key -m "$m" -f $release_tag $release_tag^{}
        )

        # Done with the fixups

        ##############################################################
        #
        #  Update the source repository from the staging repository,
        #  unless --no-update was given
        #
        #  This ensures that tags are in place to be able to create
        #  Github releases
        #
        #####

        if $do_update; then
            $ECHO "-- Pushing the release commits"
            (
                cd staging
                git push $git_quiet $source_remote_name \
                    ${ub}:${update_branch} $release_tag
            )

            # If the original source repository is on github.com, we need
            # to wait on the mirroring job that's pushing it there.  That'll
            # ensure that correct Github releases can be created, especially
            # with tags in mind.
            if [[ "$orig_source_repository" =~ ^(https?://|git@)github.com[/:] ]]; then
                $ECHO -n "-- Waiting for $release_tag to appear on $orig_source_repository."
                while [ -z "$(git ls-remote --tags \
                                  $orig_source_repository $release_tag)" ]; do
                    sleep;
                    $ECHO -n "."
                done
                $ECHO "!"
            fi
        fi

        ##############################################################
        #
        #  Create Github releases, unless --no-upload was given, or there
        #  is no Github release repository given.
        #
        #####

        if $do_gh_upload && [ -n "$gh_release_repository" ]; then
            $ECHO "-- Creating a Github release"
            gh release create --repo $gh_release_repository \
               --title "$release_text" --notes "$newsflash" \
               $release_tag "${new_upload_files[@]}"
        fi

        ##############################################################
        #
        #  Move the release files to the approriate file upload location,
        #  unless --no-upload was given, or there is no upload location
        #  given.
        #
        #####

        if $do_file_upload && [ -n "$upload_location" ]; then
            $ECHO "-- Moving release files to file service directory"
            # Move old files, only for public releases
            if [[ "$release_type" == "public" \
                      && -d "$upload_location/old/$release_series" ]]; then
            $VERBOSE "--   Moving away older release files"
                mv $upload_location/openssl-$release_series* \
                   $upload_location/old/$release_series/
            fi

            $VERBOSE "--   Copying new release files to $upload_location"
            # Copy the new release files into the release
            cp "${new_upload_files[@]}" $upload_location/
        fi

        ##############################################################
        #
        #  Update the newsflash file, unless --no-update was given
        #
        #####

        if $do_update; then
            $ECHO "-- Updating newsflash"
            (
                cd data

                awk_prg='
!found && /^[0-9]{2}-[A-Z][a-z]{2}-[0-9]{4}:/ { print d, n; found=1 }
{ print }
'
                awk -v d="$(LANG=C date +%d-%b-%Y:)" -v n="$newsflash" \
                    -e "$awk_prg" newsflash.txt > newsflash.txt.updated
                mv newsflash.txt.updated newsflash.txt
                git add newsflash.txt
                git commit $git_quiet -m "Update newsflash.txt for $version release"
            )
        fi

        ##############################################################
        #
        #  Clean up
        #
        #####
        rm "${new_upload_files[@]}"
        rm "$staging_location"/"$d"
    )
done

if $do_update; then
    $ECHO "== Update the data repository"
    (
        cd data
        git push $git_quiet
    )

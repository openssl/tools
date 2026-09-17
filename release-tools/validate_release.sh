#!/bin/sh

####################################################################
# Usage: validate_release.sh <release-tag>
#
# Requirements for usage
#
# 1) You need to have the following tools installed
# a) gpg
# b) jq
# c) ghcli
#
# Additional requirements
# 1) you must be authenticated in ghcli as a user that has access to draft releases
# 2) You must have the openssl public key imported to your gpg key ring
######################################################################

TEMPDIR=$(mktemp -d /tmp/validation.XXXXXX)

trap "rm -rf $TEMPDIR" EXIT

RELEASE=$1

mkdir $TEMPDIR/assets
cd $TEMPDIR/assets

# check tool status 
if ! command -v jq >/dev/null 2>&1; then
    echo "You must have jq installed to use this tool"
    exit 1
fi

if ! command -v gpg >/dev/null 2>&1; then
    echo "You must have gpg installed to use this tool"
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "You must have gh installed to use this tool"
    exit 1
fi

# Ensure the openssl public key is in our keyring
gpg --list-keys BA5473A2B0587B07FB27CF2D216094DFD0CB81EF >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "OpenSSL GPG key not found in keyring, can't validate release"
    echo "Please import openssls gpg public key from https://keys.openpgp.org/vks/v1/by-fingerprint/BA5473A2B0587B07FB27CF2D216094DFD0CB81EF"
    exit 1
fi

# Ensure we are logged in via gh
gh auth status
if [ $? -ne 0 ]; then
    echo "Not logged into github, please authenticate via gh auth login"
    exit 1
fi

# Get the release
echo "Downloading release artifacts for $RELEASE"
gh release download -R openssl/openssl $RELEASE

if [ $? -ne 0 ]; then
    echo "Release download failed"
    exit 1
fi

# Validate the signatures and sha256/sha1 sums
echo "Verifying archive signature"
gpg --verify $RELEASE.tar.gz.asc $RELEASE.tar.gz

if [ $? -ne 0 ]; then
    echo "Release Signature validation failed"
    exit 1
fi

echo "Verifying archive sha1sum"
sha1sum --check $RELEASE.tar.gz.sha1

if [ $? -ne 0 ]; then
    echo "Release SHA1sum validation failed"
    exit 1
fi

echo "Verifying archive sha256sum"
sha256sum --check $RELEASE.tar.gz.sha256

if [ $? -ne 0 ]; then
    echo "Release SHA1sum validation failed"
    exit 1
fi

SKIP_SBOM=no
if [ ! -f $RELEASE.sbom.asc ]; then
    echo "This release has no SBOM artifact, is that expected[n/y]?"
    read ANSWER
    case "$ANSWER" in
        y*)
            SKIP_SBOM=yes
            ;;
        *)
            echo "Failing validation as we expect an SBOM artifact"
            exit 1
            ;;
    esac
fi

if [ "$SKIP_SBOM" == "yes" ]; then
    echo "Skipping SBOM signature validation"
else
    echo "Verifying SBOM signature"
    gpg --verify $RELEASE.sbom.asc $RELEASE.sbom

    if [ $? -ne 0 ]; then
        echo "SBOM signature validation failed"
        exit 1
    fi
fi

# Extract the archive, and fetch the corresponding git tag
echo "Extracting archive"
tar xf $RELEASE.tar.gz

if [ $? -ne 0 ]; then
    echo "Extract of archive failed"
    exit 1
fi

echo "Cloning repository"
git clone --branch $RELEASE --single-branch https://github.com/openssl/openssl

if [ $? -ne 0 ]; then
    echo "Git clone failed"
    exit 1
fi
GITTAGCOMMIT=$(cd openssl; git rev-parse HEAD)

if [ "$SKIP_SBOM" == "no" ]; then
    echo "Validating SBOM contents..this will take a moment"

    SBOMFILE=./$RELEASE.sbom
    for archivefile in $(cd $RELEASE; find * -type f); do
       if [ ! -s $RELEASE/$archivefile ]; then
         echo "$archivefile is zero length, skipping"
         continue
       fi
       GITSHA256=$(sha256sum openssl/$archivefile | awk '{print $1}')
       SBOMFILE256=$(sha256sum $RELEASE/$archivefile | awk '{print $1}')
       SBOM256=$(jq -r --arg sbfile "$archivefile" '.files[] | select(has("fileName")) | select(.fileName==$sbfile) | .checksums[1].checksumValue' $SBOMFILE)
       # every non-zero length file in the archive needs to have an SBOM entry
       if [ "$SBOM256" == "" ]; then
         echo "$archivefile is missing from SBOM, failing validation!"
         exit 1
       fi
       if [ "$GITSHA256" != "$SBOM256" ]; then
         echo "$archivefile sha256sums don't match between git and release tarball!"
         exit 1
       fi
       if [ "$GITSHA256" != "$SBOMFILE256" ]; then
         echo "$archivefile sha256sums don't match between sbom and release tarball!"
         exit 1
       fi
    done
fi

echo "====================================================="
echo "Release integrity validated!"
cat  $RELEASE.tar.gz.sha1
cat  $RELEASE.tar.gz.sha256
echo "GIT TAG COMMIT $GITTAGCOMMIT"
echo "====================================================="
exit 0


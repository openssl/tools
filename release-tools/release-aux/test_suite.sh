#! /usr/bin/env bash
# Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# This script runs a test suite to check the functions in release-state-fn.sh
# and release-version-fn.sh.  It does this by setting up a small temporary
# repository with just enough fake data (in include/openssl/opensslv.h or
# VERSION.dat) to see that version data is updated correctly.

DEBUG=:
export LANG=C

HERE=$(cd $(dirname $0); pwd)
. $HERE/release-state-fn.sh
. $HERE/release-version-fn.sh

today="$(date '+%-d %b %Y')"

repo=release-test-$$.git
git init --quiet /var/tmp/$repo
cd /var/tmp/$repo
trap "cd $HERE; rm -rf /var/tmp/$repo" EXIT

echo "===== OpenSSL 3.0 version scheme"

cat > VERSION.dat <<_____
MAJOR=3
MINOR=2
PATCH=0
PRE_RELEASE_TAG=dev
BUILD_METADATA=
RELEASE_DATE=""
SHLIB_VERSION=3
_____
git add VERSION.dat
git commit -m 'Fake 3.2.0-dev' --quiet

declare -A expected

function check () {
    local errs=0

    for key in "${!expected[@]}"; do
        if [ "${!key}" != "${expected[$key]}" ]; then
            (( errs++ ))
        fi
    done

    if [ $errs -gt 0 ]; then
        echo >&2 "Got the wrong data:"
        for key in "${!expected[@]}"; do
            echo >&2 "    \$$key=${!key}"
        done
        echo >&2 "Expected:"
        for key in "${!expected[@]}"; do
            echo >&2 "    \$$key=${expected[$key]}"
        done
        exit 1
    fi
}

echo "Initial read of VERSION.DAT"
expected=(
    [TYPE]=dev
    [SERIES]=3.2
    [VERSION]=3.2.0
    [FULL_VERSION]=3.2.0-dev
    [PRE_RELEASE_TAG]=dev
    [SHLIB_VERSION]=3
    [RELEASE_FILES]='CHANGES.md;NEWS.md'
)
get_version
check

echo "Test release of 3.2.0-alpha1"
expected=(
    [TYPE]=
    [VERSION]=3.2.0
    [FULL_VERSION]=3.2.0-alpha1
    [PRE_RELEASE_TAG]=alpha1
    [RELEASE_DATE]="$today"
)
next_release_state alpha
check

echo "Test post-release of 3.2.0-alpha1"
expected=(
    [TYPE]=dev
    [VERSION]=3.2.0
    [FULL_VERSION]=3.2.0-alpha2-dev
    [PRE_RELEASE_TAG]=alpha2-dev
    [RELEASE_DATE]=
)
next_release_state alpha
check

echo "Test release of 3.2.0-beta1"
expected=(
    [TYPE]=
    [VERSION]=3.2.0
    [FULL_VERSION]=3.2.0-beta1
    [PRE_RELEASE_TAG]=beta1
    [RELEASE_DATE]="$today"
)
next_release_state beta
check

echo "Test post-release of 3.2.0-beta1"
expected=(
    [TYPE]=dev
    [VERSION]=3.2.0
    [FULL_VERSION]=3.2.0-beta2-dev
    [PRE_RELEASE_TAG]=beta2-dev
    [RELEASE_DATE]=
)
next_release_state beta
check

echo "Test release of 3.2.0"
expected=(
    [TYPE]=
    [VERSION]=3.2.0
    [FULL_VERSION]=3.2.0
    [PRE_RELEASE_TAG]=
    [RELEASE_DATE]="$today"
)
next_release_state final
check

echo "Test post-release of 3.2.0"
expected=(
    [TYPE]=dev
    [VERSION]=3.2.1
    [FULL_VERSION]=3.2.1-dev
    [PRE_RELEASE_TAG]=dev
    [RELEASE_DATE]=
)
next_release_state final
check

echo "Test release of 3.2.1"
expected=(
    [TYPE]=
    [VERSION]=3.2.1
    [FULL_VERSION]=3.2.1
    [PRE_RELEASE_TAG]=
    [RELEASE_DATE]="$today"
)
next_release_state ''
check

echo "Test post-release of 3.2.1"
expected=(
    [TYPE]=dev
    [VERSION]=3.2.2
    [FULL_VERSION]=3.2.2-dev
    [PRE_RELEASE_TAG]=dev
    [RELEASE_DATE]=
)
next_release_state ''
check

echo "Test switch to next minor release (3.3.0-dev)"
expected=(
    [TYPE]=dev
    [VERSION]=3.3.0
    [FULL_VERSION]=3.3.0-dev
    [PRE_RELEASE_TAG]=dev
    [RELEASE_DATE]=
)
next_release_state minor
check

echo "Test writing $VERSION_FILE"
set_version
cat > expected-VERSION.dat <<_____
MAJOR=3
MINOR=3
PATCH=0
PRE_RELEASE_TAG=dev
BUILD_METADATA=
RELEASE_DATE=""
SHLIB_VERSION=3
_____
if ! diff_output="$(diff -u expected-VERSION.dat VERSION.dat)"; then
    echo >&2 "$diff_output"
    exit 1
fi

echo "===== OpenSSL 1.0.2 version scheme"

git restore .
git rm --quiet VERSION.dat
mkdir crypto
cat > crypto/opensslv.h <<_____
# define OPENSSL_VERSION_NUMBER  0x10002210L
# ifdef OPENSSL_FIPS
#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zh-fips-dev  xx XXX xxxx"
# else
#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zh-dev  xx XXX xxxx"
# endif
# define OPENSSL_VERSION_PTEXT   " part of " OPENSSL_VERSION_TEXT
_____
touch openssl.spec
git add openssl.spec crypto/opensslv.h
git commit -m 'Fake 1.0.2zh-dev' --quiet

echo "Test initial read of crypto/opensslv.h"
expected=(
    [TYPE]=dev
    [SERIES]=1.0.2
    [VERSION]=1.0.2zh
    [FULL_VERSION]=1.0.2zh-dev
    [PRE_RELEASE_TAG]=dev
    [SHLIB_VERSION]=1.0.0
    [RELEASE_FILES]='README;CHANGES;NEWS;openssl.spec'
)
get_version
check

echo "Test release of 1.0.2zh"
expected=(
    [TYPE]=
    [VERSION]=1.0.2zh
    [FULL_VERSION]=1.0.2zh
    [PRE_RELEASE_TAG]=
    [RELEASE_DATE]="$today"
)
next_release_state ''
check

echo "Test post-release of 1.0.2zh"
expected=(
    [TYPE]=dev
    [VERSION]=1.0.2zi
    [FULL_VERSION]=1.0.2zi-dev
    [PRE_RELEASE_TAG]=dev
    [RELEASE_DATE]=
)
next_release_state ''
check
    
echo "Test writing $VERSION_FILE"
set_version
cat > crypto/expected-opensslv.h <<_____
# define OPENSSL_VERSION_NUMBER  0x10002220L
# ifdef OPENSSL_FIPS
#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zi-fips-dev  xx XXX xxxx"
# else
#  define OPENSSL_VERSION_TEXT    "OpenSSL 1.0.2zi-dev  xx XXX xxxx"
# endif
# define OPENSSL_VERSION_PTEXT   " part of " OPENSSL_VERSION_TEXT
_____
if ! diff_output="$(diff -u crypto/expected-opensslv.h crypto/opensslv.h)"; then
    echo >&2 "$diff_output"
    exit 1
fi

echo "===== PASS ====="

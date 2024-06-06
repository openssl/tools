#! /bin/bash
# Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# Public or premium release?  Let the version numbers determine it!
declare -A _ossl_release_types=(
    [premium]='^1\.'
    [public]='^[3-9]\.'
)

std_release_type () {
    local v=$1
    local rt
    local re
    local release_type=

    for rt in "${!_ossl_release_types[@]}"; do
        re="${_ossl_release_types[$rt]}"
        if [[ "$v" =~ $re ]]; then
            release_type=$rt
            break
        fi
    done
    echo $release_type
}

#! /bin/bash -e
# Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# format_string - Function to apply a string format on branch name, tag name
# and version, in combination
#
# Takes:
#
# $1    fmt
# $2... set of replacement directives in the form {c}={str}, where {c}
#       is a single character, and {str} is the string a % followed by
#       that character should be replaced with.
#
# Returns:
#
# Resulting string

format_string ()
{
    local fmt="$1"; shift
    local result=""

    eval $(echo "local -A directives=($( for x in "$@"; do echo " [${x%%=*}]='${x#*=}'"; done ))")
        
    while [ -n "$fmt" ]; do
        eval $(echo "$fmt" | sed -E -e 's/"/\\"/g' -e 's/^([^%]*)(%(.)(.*))?$/local PRE="\1" C="\3" POST="\4"/')
        MID=
        if [ -n "$C" ]; then
            for K in "${!directives[@]}"; do
                if [ "$C" == "$K" ]; then
                    MID="${directives[$K]}"
                    break
                fi
                # To signal that this wasn't the found directive
                K=
            done
            if [ -z "$K" ]; then
                echo >&2 "Unknown % directive: $C"
                exit 1
            fi
        fi
        result="$result$PRE$MID"
        fmt="$POST"
    done
    echo "$result"
}

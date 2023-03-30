#! /bin/bash -e
# Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# These functions all perform uploads, using sftp commands.
# They all expect two parameters:
#
# $1    The destination, properly formed for the backend.
#       In other words, it must be usable with SFTP for the sftp backend,
#       and it must be a proper existing directory for the file backend.
# $2    A flag, saying if the upload should (true) or shouldn't (false)
#       be performed.  In verbose mode (governed by the variable $VERBOSE)
#       this is useful to output what would happen if uploading was enabled.
#
# They also use the variable $VERBOSE as a command to perform verbose output.
# They may also use the variable $DEBUG as a command to perform debugging
# output.
# These variable must be set accordingly by the loading script.  Recommended
# values are ':' for non-verbose and 'echo' for verbose'

upload_backend_sftp () {
    local to=$1
    local do_upload=$2

    if [ -z "$to" ]; then
        echo >&2 "No SFTP address was provided"
        exit 1
    fi
    if [ -z "$do_upload" ]; then
        echo >&2 "Upload or not?  The flag hasn't been set"
        exit 1
    fi

    if $do_upload; then
        sftp $to
    else
        $VERBOSE "Would 'sftp $to' with the following commands:"
        while read L; do
            $VERBOSE "  $L"
        done
    fi
}

upload_backend_file () {
    local dest=$1
    local do_upload=$2

    if [ -z "$dest" ]; then
        echo >&2 "No destination directory was provided"
        exit 1
    fi
    if ! [ -d "$dest" ]; then
        echo >&2 "Not a directory: $dest"
        exit 1
    fi
    if [ -z "$do_upload" ]; then
        echo >&2 "Upload or not?  The flag hasn't been set"
        exit 1
    fi

    (
        progress=
        while read L; do
            set -- $L
            case $1 in
                progress )
                    if [ -z "$progress" ]; then
                        progress=-v
                    else
                        progress=
                    fi
                    ;;
                cd )
                    if [ -d "$dest/$2" ]; then
                        dest="$dest/$2"
                    else
                        echo >&2 "Warning: Not a directory: $dest/$2"
                    fi
                    ;;
                put )
                    if $do_upload; then
                        cp $progress $2 $dest/$3
                    else
                        $VERBOSE "Would copy $2 -> $dest/$3"
                    fi
                    ;;
                * )
                    echo >&2 "Warning: Unknown command: $@"
                    ;;
            esac
        done
    )
}

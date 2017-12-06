#!/bin/bash

#Script for emergency cleanup of the run-checker.sh work directory
#Place this script in the same directory as run-checker.sh

#This really just runs the takedown hook, so unless there are any
#hooks present, nothing at all will happen.

here=$(cd $(dirname $0); pwd)

run-hook () {
    local hookname=$1; shift
    if [ -x $here/hook-$hookname ]; then
        (cd $here; ./hook-$hookname "$@")
    fi
}

run-hook takedown

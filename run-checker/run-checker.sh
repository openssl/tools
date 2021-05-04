#!/bin/bash

#Script to check all available no- options
#Place this script in an empty directory (apart from a few hook scripts,
#read on).
#In the same directory clone openssl into an openssl subdir.
#Then run the script.

#Some hook scripts can be placed in the same directory and are execute if
#present.  They are:
#
# hook-prepare  - called before anything starts
# hook-start    - called before each option is getting built
#                 Takes one argument:
#                   $1   the option being built, which is also the build dir
#                   $2.. the expanded options
# hook-end      - called after each option has been built
#                 Takes two arguments:
#                   $1   the option being built, which is also the build dir
#                   $2   "pass" or "fail"
# hook-takedown - called at the very end

here=$(cd $(dirname $0); pwd)
opts=( ''
no-afalgeng enable-asan no-asm no-async no-autoalginit no-autoerrinit
no-bf no-blake2 no-camellia no-capieng no-cast no-chacha no-cmac no-cms no-comp
enable-crypto-mdebug enable-crypto-mdebug-backtrace no-ct no-deprecated no-des
no-dgram no-dh no-dsa no-dso no-dynamic-engine no-ec no-ec2m no-ecdh
no-ecdsa enable-ec_nistp_64_gcc_128 enable-egd no-engine 'no-engine no-shared'
no-err no-filenames
no-aria no-asan no-crypto-mdebug no-crypto-mdebug-backtrace no-devcryptoeng
no-ec_nistp_64_gcc_128 no-egd no-external-tests no-fuzz-afl no-fuzz-libfuzzer
no-heartbeats no-md2 no-msan no-rc5 no-sctp no-ssl no-ssl-trace no-tests
no-ubsan no-ui-console no-unit-test no-weak-ssl-ciphers
no-zlib no-zlib-dynamic
enable-fuzz-afl enable-fuzz-libfuzzer enable-heartbeats no-hw no-hw-padlock
no-idea no-makedepend enable-md2 no-md4 no-mdc2 no-gost no-multiblock
no-nextprotoneg no-ocb no-ocsp no-pic no-poly1305 no-posix-io no-psk no-rc2
no-rc4 enable-rc5 no-rdrand no-rfc3779 no-ripemd no-rmd160 no-scrypt enable-sctp
no-seed no-shared no-sock no-srp no-srtp no-sse2 enable-ssl-trace
no-static-engine no-stdio no-threads no-ts enable-ubsan no-ui
enable-unit-test no-whirlpool enable-weak-ssl-ciphers enable-zlib
enable-zlib-dynamic 386 no-dtls no-tls no-ssl3 no-tls1 no-tls1_1 no-tls1_2
no-dtls1 no-dtls1_2 no-ssl3-method no-tls1-method no-tls1_1-method
no-tls1_2-method no-dtls1-method no-dtls1_2-method no-siphash no-tls1_3 no-sm2
no-sm3 no-sm4 enable-trace no-legacy no-cached-fetch no-autoload-config
'no-buildtest-c++' no-bulk no-cmp no-ktls no-module no-padlockeng
no-pinshared no-secure-memory no-siv no-uplink enable-acvp-tests enable-fips
'enable-fips no-fips-securitychecks' 'enable-fips enable-acvp-tests'
'enable-fips no-tls' 'enable-fips no-tls1_1' 'enable-fips no-tls1'
'enable-fips no-ssl3-method' 'enable-fips no-tls1-method'
'enable-fips no-tls1_1-method' 'enable-fips no-tls1_3'
)

run-hook () {
    local hookname=$1; shift
    if [ -x $here/hook-$hookname ]; then
        (cd $here; ./hook-$hookname "$@")
    fi
}

log-eval () {
    echo \$ "$@"
    eval "$@"
}

log-exec () {
    echo \$ "$@"
    exec "$@"
}

rkill () {
    local signal=$1; shift
    local pid=$1; shift
    local notpid=$1; shift

    if children="$(pgrep -P "$pid")"; then
        for child in $children; do
            rkill "$signal" "$child" "$notpid"
        done
    fi
    if [ "$pid" != "$notpid" ]; then
        kill -s "$signal" "$pid"
    fi
}

if [ ! -d openssl/.git ]; then
    echo >&2 "Missing openssl checkout in openssl/"
    exit 1
fi

if run-hook prepare; then
    for req_binary in clang afl-clang-fast; do
        which $req_binary >/dev/null 2>&1
        if [ "$?" != "0" ]; then
            echo "Warning: $req_binary does not appear to be in PATH"
        fi
    done
    for opt in "${opts[@]}";
    do
        expandedopts="$opt"
        warnopts="--strict-warnings"
        optcc="clang"
        ldcmd=""
        gost_engine="$OPENSSL_GOST_ENGINE_SO"

        if [ "$opt" == "enable-asan" ]; then
            # A documented requirement for enable-asan is no-shared
            expandedopts="enable-asan no-shared no-asm -DOPENSSL_SMALL_FOOTPRINT"
        elif [ "$opt" == "enable-ubsan" ]; then
            # We've seen it on Travis already, ubsan requires -DPEDANTIC and
            # -fno-sanitize=alignment, or crypto/modes will fail to build in
            # some circumstances.  Running on a VM seems to be one of them.
            expandedopts="enable-ubsan no-asm -DPEDANTIC -DOPENSSL_SMALL_FOOTPRINT -fno-sanitize=alignment"
        elif [ "$opt" == "enable-fuzz-afl" ]; then
            warnopts=""
            optcc=afl-clang-fast 
            expandedopts="enable-fuzz-afl no-shared no-module"
        elif [ "$opt" == "enable-fuzz-libfuzzer" ]; then
            warnopts=""
            ldcmd=clang++
            expandedopts="enable-fuzz-libfuzzer --with-fuzzer-include=../../Fuzzer --with-fuzzer-lib=../../Fuzzer/libFuzzer -DPEDANTIC enable-asan enable-ubsan no-shared"
        elif [ "$opt" == "no-static-engine" ]; then
            expandedopts="no-static-engine no-shared"
        elif [ "$opt" == "no-deprecated" ]; then
            #The gost engine uses some deprecated symbols so we don't use it
            #in a no-deprecated build
            gost_engine=""
        elif [ "$opt" == "no-cached-fetch" ]; then
            expandedopts="no-cached-fetch enable-asan enable-ubsan"
        fi

        if [ -z "$opt" ]; then
            builddir=default
        else
            builddir="$(echo $opt | sed -e 's|[ /]|_|g')"
        fi
        if run-hook start "$builddir" "$opt" -d $warnopts $expandedopts; then
            if (
                set -e

                if [ ! -d "./$builddir" ]; then
                   mkdir "./$builddir"
                fi
                cd "./$builddir"

                echo "Building with '$opt'"
                log-eval \
                    CC=$optcc ../openssl/config -d $warnopts $expandedopts \
                    >build.log 2>&1 || \
                    exit $?

                echo "  make clean"
                log-eval make clean >>build.log 2>&1 || exit $?

                echo "  make depend"
                log-eval make depend >>build.log 2>&1 || exit $?

                echo "  make -j4"
                log-eval LDCMD=$ldcmd make -j4 >>build.log 2>&1 || exit $?

                # Because 'make test' may hang under certain circumstances,
                # we have a timeout mechanism around it.
                (
                    testpid=$BASHPID

                    # Number of seconds to wait for command completion.
                    # (3600 = one hour)
                    timeout=3600
                    # Interval between checks if the process is still alive.
                    interval=5
                    # Delay between posting the SIGTERM signal and destroying
                    # the process by SIGKILL.
                    delay=1

                    # kill -0 pid
                    # Exit code indicates if a signal may be sent to $testpid
                    # process.
                    (
                        ((t = timeout))

                        while ((t > 0)); do
                            sleep $interval
                            kill -0 $testpid || exit 0
                            ((t -= interval))
                        done

                        # Be nice, post SIGTERM first.
                        # The 'exit 0' below will be executed if any preceeding
                        # command fails.
                        rkill SIGTERM $testpid $BASHPID && kill -0 $testpid \
                                || exit 0
                        sleep $delay
                        rkill SIGKILL $testpid $BASHPID
                    ) 2> /dev/null &

                    # If not set to another value, default to 4 test jobs
                    echo "  make test"
                    HARNESS_JOBS=${HARNESS_JOBS:-4} OPENSSL_GOST_ENGINE_SO="$gost_engine" log-exec make test >>build.log 2>&1
                )
            ); then
                echo "  PASS"
                run-hook end "$builddir" pass
            else
                echo "  FAILED"
                run-hook end "$builddir" fail
                if [ "$opt" = "" ]; then
                    break
                fi
            fi
        fi
    done

    run-hook takedown
fi

#!/usr/bin/env bash

#
#
# Copyright 2024 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
#

#
# Iterations to run each tool
#
VERSIONS=(1.1.1 3.0 3.3 master)
THREAD_COUNTS=(1 2 4 8 16 32 64 128)
ITERATIONS=25

PERFTOOLS=(
        evp_fetch
        randbytes
        handshake
        sslnew
        newrawkey
        rsasign
        x509storeissuer
        providerdoall
    )
for alg in dh dhx dsa ec rsa x25519; do
    for format in der pem; do
        PERFTOOLS=("${PERFTOOLS[@]}" pkeyread-${alg}-${format})
    done
done
# Not yet useful:
#PERFTOOLS=("${PERFTOOLS[@]}" rwlocks-rlock rwlocks-wlock)

if [ -z ${1+x} ] ; then
    echo 'output file is missing'
    exit 1
fi
RESULT=$1

touch -am $RESULT
if [ $? -ne 0 ] ; then
    echo "Can not write $RESULT"
    exit 1
fi

#
# directory where to store results
#
RESULTS=$(mktemp -d)
trap "rm -rf $RESULTS" exit

# path where all openssl versions are installed.
# each version should be installed to its prefix.
# script expects prefix to be something like
#	/path/to/openssl.installs/openssl-$version
#
# OPENSSL_BINARIES=~/work.openssl/openssl.binaries/
#
if [ -z ${OPENSSL_BINARIES+x} ] ; then
    echo "OPENSSL_BINARIES env. variable not set"
    exit 1
fi

for VERSION in "${VERSIONS[@]}" ; do
    OPENSSL_DIR=$OPENSSL_BINARIES/openssl-$VERSION
    if [ ! -d $OPENSSL_DIR ] ; then
        echo "OpenSSL $VERSION not found ($OPENSSL_DIR does not exit"
        exit 1
    fi
done

#
# directory where perf tools sources live
#
# TOOLS_PATH=~/work.openssl/tools.sashan/perf
#
if [ -z ${TOOLS_PATH+x} ] ; then
    echo "TOOLS_PATH env. variable not set"
    exit 1
fi


#
# directory where clone of github repository lives
# handshake test (et. al.) use certificates from
# there.
#
# OPENSSL_SRC=~/work.openssl/openssl/
#
if [ -z ${OPENSSL_SRC+x} ] ; then
    echo "OPENSSL_SRC env. variable not set"
    exit 1
fi
CERT_DIR=$OPENSSL_SRC/test/certs
if [ ! -d $CERT_DIR ] ; then
    echo "$CERT_DIR not found in $OPENSSL_SRC"
    exit 1
fi

function openssl.env {
    OPENSSL_VERSION=$1;
    OPENSSL_DIR=$OPENSSL_BINARIES/openssl-$OPENSSL_VERSION
    if [ -d $OPENSSL_DIR ] ; then
        #
        # OpenBSD build (and perhaps other place 64-bit version
        # to prefix/lib. while for example Debian build installs
        # openssl under prefix/lib64
        #
        if [ -d $OPENSSL_DIR/lib ] ; then
            LD_LIBRARY_PATH=$OPENSSL_DIR/lib
            # set them for perf tools testing
            TARGET_OSSL_LIBRARY_PATH=$OPENSSL_DIR/lib
            TARGET_OSSL_INCLUDE_PATH=$OPENSSL_DIR/include
            OPENSSL_HEADERS=$OPENSSL_DIR/include
            OPENSSL_LIB_PATH=$OPENSSL_DIR/lib
        elif [ -d $OPENSSL_DIR/lib64 ] ; then
            LD_LIBRARY_PATH=$OPENSSL_DIR/lib64
            # set them for perf tools testing
            TARGET_OSSL_LIBRARY_PATH=$OPENSSL_DIR/lib64
            TARGET_OSSL_INCLUDE_PATH=$OPENSSL_DIR/include
            OPENSSL_HEADERS=$OPENSSL_DIR/include
            OPENSSL_LIB_PATH=$OPENSSL_DIR/lib64
        else
            echo "$OPENSSL_DIR does not exist"
            exit 1
        fi
    else
        echo "$OPENSSL_DIR does not exist"
        exit 1
    fi
}

#
# execute all tools we have to convey performance test.
# each program we run prints single number: microseconds
# it took to run it.
#

for VERSION in "${VERSIONS[@]}" ; do
    pushd $TOOLS_PATH
    openssl.env $VERSION;
    make clean
    if [ "$VERSION" == "1.1.1" ] ; then
        TARGET_OSSL_LIBRARY_PATH=$OPENSSL_LIB_PATH \
                TARGET_OSSL_INCLUDE_PATH=$OPENSSL_HEADERS make all111
    else
        TARGET_OSSL_LIBRARY_PATH=$OPENSSL_LIB_PATH \
                TARGET_OSSL_INCLUDE_PATH=$OPENSSL_HEADERS make
    fi
    popd

    for wrap in evp_fetch randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall
    do
        if [[ -x "$TOOLS_PATH/$wrap" ]]; then
            eval "$( printf '
                function %s {
                    (LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/%s "$@")
                }\n' "$wrap" "$wrap" )"
        fi
    done
    if [[ -x "$TOOLS_PATH/pkeyread" ]]; then
        for alg in dh dhx dsa ec rsa x25519; do
            for format in der pem; do
                eval "$( printf '
                    function pkeyread-%s-%s {
                        (LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k %s -f %s "$@" | cut -d ']' -f 2 | sed -e 's/us$//g')
                    }\n' "$alg" "$format" "$alg" "$format" )"
            done
        done
    fi
    if [[ -x "$TOOLS_PATH/rwlocks" ]]; then
        function rwlocks-rlock {
            (LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/rwlocks "$@" | cut -d ' ' -f 1)
        }
        function rwlocks-wlock {
            (LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/rwlocks "$@" | cut -d ' ' -f 2)
        }
    fi

    for TOOL in "${PERFTOOLS[@]}" ; do
        CMD=$TOOLS_PATH/$TOOL

        for THREADS in "${THREAD_COUNTS[@]}" ; do
            if ! type -t $TOOL >/dev/null; then
                #
                # if tools is not available for VERSION, then
                # print N/A. We print a two cells of
                # table formatted in markdown.
                #
                printf ' N/A | N/A | ' > $RESULTS/$TOOL.$VERSION-$THREADS
                continue
            fi
            #
            # Run tool ITERATIONS times. Script then calculates
            # average time and standard deviation.
            #
	    declare -a USECS_ARRAY=()
	    for k in $(seq 1 1 $ITERATIONS) ; do
		export EVP_FETCH_TYPE=MD:MD5
		ARGS="-t $THREADS $CERT_DIR"
		echo "Running $CMD against $VERSION with $THREADS threads, iteration $k"
		OUTPUT=$($TOOL $ARGS)
		USECS=$(echo $OUTPUT | awk '{print $1}')
		USECS_ARRAY+=($USECS)
	    done
            #
            # Process samples.
            #
	    TUSECS=0
	    for value in "${USECS_ARRAY[@]}" ; do
		TUSECS=$(dc -e"$value $TUSECS + p")
	    done
	    AVG_USECS=$(dc -e"6 k $TUSECS ${#USECS_ARRAY[@]} / p")
	    declare -a USEC_DEV_ARRAY=()
	    for value in "${USECS_ARRAY[@]}" ; do
		DEVIATION=$(dc -e"6 k $value $AVG_USECS - p" | sed -e"s/-/_/g")
		DEVIATION=$(dc -e"6 k $DEVIATION $DEVIATION * p")
		USEC_DEV_ARRAY+=($DEVIATION)
	    done
	    echo ${USEC_DEV_ARRAY[@]}
	    SUM_DEVIATIONS=0
	    for value in "${USEC_DEV_ARRAY[@]}" ; do
		SUM_DEVIATIONS=$(dc -e"6 k $value $SUM_DEVIATIONS + p")
	    done
	    STD_DEVIATION=$(dc -e"6 k $SUM_DEVIATIONS ${#USECS_ARRAY[@]} 1 - / v p")
            #
            # we produce a file which holds two table cells in markdown format:
            # avg. time and std deviation.
            #
	    echo -n "$AVG_USECS | $STD_DEVIATION |" > $RESULTS/$TOOL.$VERSION-$THREADS
        done # thredas
    done # tool
done # version


#
# assemble all markdown cells to table.
#
OUT=$RESULTS/report.md
echo '' > $OUT
for TOOL in "${PERFTOOLS[@]}" ; do
    echo "### $TOOL" >> $OUT
    echo '' >> $OUT
    # print table header
    # thread count | iteration | avg. version | std. version | ....
    echo -n '|thread count| number of iterations |' >> $OUT
    for VERSION in "${VERSIONS[@]}" ; do
        echo -n "openssl $VERSION per operation avg usec | $VERSION std dev |" >> $OUT
    done
    echo '' >> $OUT
    # print table header delimeter
    echo -n '|----|----' >> $OUT #thread count | iterations
    for VERSION in "${VERSIONS[@]}" ; do
        echo -n '|----|----' >> $OUT
    done
    echo '|' >> $OUT
    for THREADS in "${THREAD_COUNTS[@]}" ; do
        echo -n "| $THREADS | $ITERATIONS |" >> $OUT
        for VERSION in "${VERSIONS[@]}" ; do
            cat $RESULTS/$TOOL.$VERSION-$THREADS >> $OUT
            rm $RESULTS/$TOOL.$VERSION-$THREADS
        done
        echo '' >> $OUT
    done
    echo '' >> $OUT
done

mv $RESULTS/report.md $RESULT

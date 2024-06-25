#!/bin/bash

#
#
# Copyright 2024 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
#

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

#
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

VERSIONS='1.1.1 3.0 3.3 master'
for VERSION in $VERSIONS ; do
    OPENSSL_DIR=$OPENSSL_BINARIES/openssl-$VERSION
    if [ ! -d $OPENSSL_DIR ] ; then
        echo "OpenSSL $VERSION not found ($OPENSSL_DIR does not exit"
        exit 1
    fi
done

PERFTOOLS='evp_fetch randbytes handshake sslnew newrawkey rsasign
        x509storeissuer providerdoall rwlocks-rlock rwlocks-wlock
	pkeyread-dh-der pkeyread-dhx-der pkeyread-dsa-der pkeyread-ec-der
	pkeyread-rsa-der pkeyread-x25519-der pkeyread-dh-pem pkeyread-dhx-pem
	pkeyread-dsa-pem pkeyread-ec-pem pkeyread-rsa-pem
	pkeyread-x25519-pem'

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

#
# Iterations to run each tool
#
ITERATIONS=25

THREAD_COUNTS='1 2 4 8 16 32 64 128'

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

function evp_fetch {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/evp_fetch $*")
}

function randbytes {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/randbytes $*")
}

function handshake {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/handshake $*")
}

function sslnew {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/sslnew $*")
}

function newrawkey {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/newrawkey $*")
}

function rsasign {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/rsasign $*")
}

function x509storeissuer {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/x509storeissuer $*")
}

function providerdoall {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/providerdoall $*")
}

function pkeyread-dh-der {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k dh -f der $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-dhx-der {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k dhx -f der $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-dsa-der {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k dsa -f der $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-ec-der {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k ec -f der $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-rsa-der {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k rsa -f der $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function  pkeyread-x25519-der {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k x25519 -f der $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-dh-pem {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k dh -f pem $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-dhx-pem {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k dhx -f pem $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-dsa-pem {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k dsa -f pem $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-ec-pem {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k ec -f pem $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-rsa-pem {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k rsa -f pem $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function pkeyread-x25519-pem {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/pkeyread -k x25519 -f pem $* | cut -d ']' -f 2 | sed -e 's/us$//g'")
}

function rwlocks-rlock {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/rwlocks $* | cut -d ' ' -f 1")
}

function rwlocks-wlock {
    (/bin/sh -c "LD_LIBRARY_PATH=$OPENSSL_LIB_PATH $TOOLS_PATH/rwlocks $* | cut -d ' ' -f 2")
}

#
# execute all tools we have to convey performance test.
# each program we run prints single number: microseconds
# it took to run it.
#
for TOOL in $PERFTOOLS ; do

    for VERSION in $VERSIONS ; do
        pushd `pwd`
        cd $TOOLS_PATH
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
        for THREADS in $THREAD_COUNTS ; do
            # pkeyread_* functions need pkyeread tool.
            TEST_TOOL=`echo $TOOL | sed -e 's/\(pkeyread\).*/\1/g'`
            TEST_TOOL=$TOOLS_PATH/$TEST_TOOL
            if [[ ! -x $TEST_TOOL ]] ; then
                #
                # if tools is not available for VERSION, then
                # print N/A. We print a two cells of
                # table formatted in markdown.
                #
                echo -n ' N/A | N/A | ' > $RESULTS/$TOOL.$VERSION-$THREADS
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
		echo "Running $TOOL against $VERSION with $THREADS threads, iteration $k"
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
    done # version
done # tool


#
# assemble all markdown cells to table.
#
OUT=$RESULTS/report.md
echo '' > $OUT
for TOOL in $PERFTOOLS ; do
    echo "### $TOOL" >> $OUT
    echo '' >> $OUT
    # print table header
    # thread count | iteration | avg. version | std. version | .... 
    echo -n '|thread count| number of iterations |' >> $OUT
    for VERSION in $VERSIONS ; do
        echo -n "openssl $VERSION per operation avg usec | $VERSION std dev |" >> $OUT
    done
    echo '' >> $OUT
    # print table header delimeter
    echo -n '|----|----' >> $OUT #thread count | iterations
    for VERSION in $VERSIONS ; do
        echo -n '|----|----' >> $OUT
    done
    echo '|' >> $OUT
    for THREADS in $THREAD_COUNTS ; do
        echo -n "| $THREADS | $ITERATIONS |" >> $OUT
        for VERSION in $VERSIONS ; do
            cat $RESULTS/$TOOL.$VERSION-$THREADS >> $OUT
            rm $RESULTS/$TOOL.$VERSION-$THREADS
        done
        echo '' >> $OUT
    done
    echo '' >> $OUT
done

mv $RESULTS/report.md $RESULT

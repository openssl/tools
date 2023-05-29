/*
 * Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <openssl/rand.h>
#include <openssl/crypto.h>
#include <openssl/provider.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  100
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

static int err = 0;

static int doit(OSSL_PROVIDER *provider, void *vcount)
{
    int *count = vcount;

    (*count)++;
    return 1;
}

static void do_providerdoall(size_t num)
{
    int i;
    unsigned char buf[32];
    int count;

    for (i = 0; i < NUM_CALLS_PER_THREAD; i++) {
        count = 0;
        if (!OSSL_PROVIDER_do_all(NULL, doit, &count) || count != 1) {
            err = 1;
            break;
        }
    }
}

int main(int argc, char *argv[])
{
    int threadcount;
    OSSL_TIME duration;
    uint64_t us;
    double calltime;
    int terse = 0;
    int argnext;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: providerdoall [--terse] threadcount\n");
        return EXIT_FAILURE;
    }

    if (argc == 3) {
        terse = 1;
        argnext = 2;
    } else {
        argnext = 1;
    }

    threadcount = atoi(argv[argnext]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        return EXIT_FAILURE;
    }

    if (!perflib_run_multi_thread_test(do_providerdoall, threadcount, &duration)) {
        printf("Failed to run the test\n");
        return EXIT_FAILURE;
    }

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    calltime = (double)us / (NUM_CALL_BLOCKS_PER_THREAD * threadcount);

    if (terse)
        printf("%lf\n", calltime);
    else
        printf("Total time divided by num blocks of %d OSSL_PROVIDER_do_all() calls: %lfus\n",
               NUM_CALLS_PER_BLOCK, calltime);

    return EXIT_SUCCESS;
}

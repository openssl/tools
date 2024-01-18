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
#include "perflib/perflib.h"

#define NUM_CALLS_PER_BLOCK         1000
#define NUM_CALL_BLOCKS_PER_RUN     100
#define NUM_CALLS_PER_RUN           (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_RUN)

int err = 0;

static int threadcount;

void do_randbytes(size_t num)
{
    int i;
    unsigned char buf[32];

    for (i = 0; i < NUM_CALLS_PER_RUN / threadcount; i++)
        if (!RAND_bytes(buf, sizeof(buf)))
            err = 1;
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration;
    uint64_t us;
    double avcalltime;
    int terse = 0;
    int argnext;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: randbytes [--terse] threadcount\n");
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

    if (!perflib_run_multi_thread_test(do_randbytes, threadcount, &duration)) {
        printf("Failed to run the test\n");
        return EXIT_FAILURE;
    }

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    avcalltime = (double)us / NUM_CALL_BLOCKS_PER_RUN;

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per %d RAND_bytes() calls: %lfus\n",
            NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}

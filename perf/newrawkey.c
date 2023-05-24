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
#include <openssl/evp.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  100
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

int err = 0;

static unsigned char buf[32] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b,
    0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f
};

void do_newrawkey(size_t num)
{
    int i;
    EVP_PKEY *pkey;

    for (i = 0; i < NUM_CALLS_PER_THREAD; i++) {
        pkey = EVP_PKEY_new_raw_public_key_ex(NULL, "X25519", NULL, buf,
                                              sizeof(buf));
        if (pkey == NULL)
            err = 1;
        else
            EVP_PKEY_free(pkey);
    }
}

int main(int argc, char *argv[])
{
    int threadcount;
    OSSL_TIME duration;
    uint64_t us;
    double avcalltime;
    int terse = 0;
    int argnext;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: newrawkey [--terse] threadcount\n");
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

    if (!perflib_run_multi_thread_test(do_newrawkey, threadcount, &duration)) {
        printf("Failed to run the test\n");
        return EXIT_FAILURE;
    }

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    avcalltime = (double)us / (NUM_CALL_BLOCKS_PER_THREAD * threadcount);

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per %d EVP_PKEY_new_raw_public_key_ex() calls: %lfus\n",
               NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}

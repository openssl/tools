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

#define NUM_CALLS_PER_TEST         100000

OSSL_TIME *times;

int err = 0;

static unsigned char buf[32] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b,
    0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f
};

static int threadcount;

void do_newrawkey(size_t num)
{
    int i;
    EVP_PKEY *pkey;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_CALLS_PER_TEST / threadcount; i++) {
        pkey = EVP_PKEY_new_raw_public_key_ex(NULL, "X25519", NULL, buf,
                                              sizeof(buf));
        if (pkey == NULL)
            err = 1;
        else
            EVP_PKEY_free(pkey);
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration;
    OSSL_TIME us;
    double av;
    int terse = 0;
    int argnext;
    size_t i;
    int rc = EXIT_FAILURE;

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

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        return EXIT_FAILURE;
    }

    if (!perflib_run_multi_thread_test(do_newrawkey, threadcount, &duration)) {
        printf("Failed to run the test\n");
        goto out;
    }

    if (err) {
        printf("Error during test\n");
        goto out;
    }

    us = times[0];
    for (i = 1; i < threadcount; i++)
        us = ossl_time_add(us, times[i]);
    us = ossl_time_divide(us, NUM_CALLS_PER_TEST);

    /*
     * EVP_PKEY_new_raw_public_key is pretty fast, running in
     * only a few us.  But ossl_time2us does integer division
     * and so because the average us computed above is less than
     * the value of OSSL_TIME_US, we wind up with truncation to
     * zero in the math.  Instead, manually do the division, casting
     * our values as doubles so that we comput the proper time
     */
    av = (double)ossl_time2ticks(us)/(double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", av);
    else
        printf("Average time per EVP_PKEY_new_raw_public_key_ex() call: %lfus\n",
               av);

    rc = EXIT_SUCCESS;
out:
    OPENSSL_free(times);
    return rc;
}

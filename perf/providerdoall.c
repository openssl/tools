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

#define NUM_CALLS_PER_TEST         100000

static int err = 0;
OSSL_TIME *times;

static int doit(OSSL_PROVIDER *provider, void *vcount)
{
    int *count = vcount;

    (*count)++;
    return 1;
}

static int threadcount;

static void do_providerdoall(size_t num)
{
    int i;
    unsigned char buf[32];
    int count;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_CALLS_PER_TEST / threadcount; i++) {
        count = 0;
        if (!OSSL_PROVIDER_do_all(NULL, doit, &count) || count != 1) {
            err = 1;
            break;
        }
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);
}

int main(int argc, char *argv[])
{
    int i;
    OSSL_TIME duration, us;
    double av;
    int terse = 0;
    int argnext;
    int ret = EXIT_FAILURE;

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

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        goto err;
    }

    if (!perflib_run_multi_thread_test(do_providerdoall, threadcount, &duration)) {
        printf("Failed to run the test\n");
        goto err;
    }

    if (err) {
        printf("Error during test\n");
        goto err;
    }

    us = times[0];
    for (i = 1; i < threadcount; i++)
        us = ossl_time_add(us, times[i]);
    us = ossl_time_divide(us, NUM_CALLS_PER_TEST);

    av = (double)ossl_time2ticks(us) / (double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", av);
    else
        printf("Average time per OSSL_PROVIDER_do_all() call: %lfus\n",
               av);

    ret = EXIT_SUCCESS;
 err:
    OPENSSL_free(times);
    return ret;
}

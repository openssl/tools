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
#include <openssl/ssl.h>
#include "perflib/perflib.h"

#define NUM_CTX_PER_RUN        100000

int err = 0;

OSSL_TIME *times;

static int threadcount;

static void do_create_ctx(size_t num)
{
    int ret = 1;
    int i;
    SSL_CTX *ctx = NULL;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_CTX_PER_RUN / threadcount; i++) {
        ctx = SSL_CTX_new(TLS_server_method());
        if (ctx == NULL)
            goto out;
        SSL_CTX_free(ctx);
        ctx == NULL;
    }

out:
    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);

    if (!ret)
        err = 1;
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration, ttime;
    uint64_t us;
    double avcalltime;
    int ret = EXIT_FAILURE;
    int i;
    int argnext;
    int terse = 0;

    if ((argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: ssl_ctx [--terse] threadcount\n");
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
        goto err;
    }

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        goto err;
    }

    if (!perflib_run_multi_thread_test(do_create_ctx, threadcount, &duration)) {
        printf("Failed to run the test\n");
        goto err;
    }

    if (err) {
        printf("Error during test\n");
        goto err;
    }

    ttime = times[0];
    for (i = 1; i < threadcount; i++)
        ttime = ossl_time_add(ttime, times[i]);

    avcalltime = ((double)ossl_time2ticks(ttime) / (double)NUM_CTX_PER_RUN) / (double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per ssl_ctx call: %lfus\n", avcalltime);

    ret = EXIT_SUCCESS;
 err:
    OPENSSL_free(times);
    return ret;
}

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
#include <openssl/crypto.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_TEST         100000

int err = 0;
static SSL_CTX *ctx;

static int threadcount;
static OSSL_TIME *times = NULL;

void do_sslnew(size_t num)
{
    int i;
    SSL *s;
    BIO *rbio, *wbio;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_CALLS_PER_TEST / threadcount; i++) {
        s = SSL_new(ctx);
        rbio = BIO_new(BIO_s_mem());
        wbio = BIO_new(BIO_s_mem());

        if (s == NULL || rbio == NULL || wbio == NULL) {
            err = 1;
            BIO_free(rbio);
            BIO_free(wbio);
        } else {
            /* consumes the rbio/wbio references */
            SSL_set_bio(s, rbio, wbio);
        }

        SSL_free(s);
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration;
    OSSL_TIME ttime;
    double avcalltime;
    int terse = 0;
    int argnext;
    int rc = EXIT_FAILURE;
    size_t i;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: sslnew [--terse] threadcount\n");
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

    ctx = SSL_CTX_new(TLS_server_method());
    if (ctx == NULL) {
        printf("Failure to create SSL_CTX\n");
        goto out;
    }

    if (!perflib_run_multi_thread_test(do_sslnew, threadcount, &duration)) {
        printf("Failed to run the test\n");
        goto out;
    }

    if (err) {
        printf("Error during test\n");
        goto out;
    }

    ttime = times[0];
    for (i = 1; i < threadcount; i++)
        ttime = ossl_time_add(ttime, times[i]);

    avcalltime = ((double)ossl_time2ticks(ttime) / (double)NUM_CALLS_PER_TEST) / (double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per SSL/BIO creation call: %lfus\n",
               avcalltime);
out:
    SSL_CTX_free(ctx);
    OPENSSL_free(times);
    return rc;
}

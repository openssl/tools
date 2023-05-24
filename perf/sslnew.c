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

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  100
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

int err = 0;
static SSL_CTX *ctx;

void do_sslnew(size_t num)
{
    int i;
    SSL *s;
    BIO *rbio, *wbio;

    for (i = 0; i < NUM_CALLS_PER_THREAD; i++) {
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

    ctx = SSL_CTX_new(TLS_server_method());
    if (ctx == NULL) {
        printf("Failure to create SSL_CTX\n");
        return EXIT_FAILURE;
    }

    if (!perflib_run_multi_thread_test(do_sslnew, threadcount, &duration)) {
        SSL_CTX_free(ctx);
        printf("Failed to run the test\n");
        return EXIT_FAILURE;
    }

    SSL_CTX_free(ctx);

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    avcalltime = (double)us / (NUM_CALL_BLOCKS_PER_THREAD * threadcount);

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per %d SSL/BIO creation calls: %lfus\n",
            NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}

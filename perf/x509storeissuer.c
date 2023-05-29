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
#include <openssl/bio.h>
#include <openssl/x509.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  1000
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

static int err = 0;
static X509_STORE *store = NULL;
static X509 *x509 = NULL;
OSSL_TIME *times;

static void do_x509storeissuer(size_t num)
{
    int i;
    X509_STORE_CTX *ctx = X509_STORE_CTX_new();
    X509 *issuer = NULL;
    OSSL_TIME start, end;

    if (ctx == NULL || !X509_STORE_CTX_init(ctx, store, x509, NULL)) {
        printf("Failed to initialise X509_STORE_CTX\n");
        err = 1;
        goto err;
    }

    start = ossl_time_now();

    for (i = 0; i < NUM_CALLS_PER_THREAD; i++) {
        /*
         * We actually expect this to fail. We've not configured any
         * certificates inside our store. We're just testing calling this
         * against an empty store.
         */
        if (X509_STORE_CTX_get1_issuer(&issuer, ctx, x509) != 0) {
            printf("Unexpected result from X509_STORE_CTX_get1_issuer\n");
            err = 1;
            X509_free(issuer);
            goto err;
        }
        issuer = NULL;
    }

    end = ossl_time_now();
    times[num] = ossl_time_divide(ossl_time_subtract(end, start),
                                  NUM_CALL_BLOCKS_PER_THREAD);

 err:
    X509_STORE_CTX_free(ctx);
}

int main(int argc, char *argv[])
{
    int threadcount, i;
    OSSL_TIME duration, av;
    uint64_t us;
    double avcalltime;
    int terse = 0;
    int argnext;
    char *cert;
    int ret = EXIT_FAILURE;
    BIO *bio;

    if ((argc != 3 && argc != 4)
            || (argc == 4 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: x509storeissuer [--terse] certsdir threadcount\n");
        return EXIT_FAILURE;
    }

    if (argc == 4) {
        terse = 1;
        argnext = 2;
    } else {
        argnext = 1;
    }

    cert = perflib_mk_file_path(argv[argnext], "servercert.pem");
    if (cert == NULL) {
        printf("Failed to allocate cert\n");
        goto err;
    }

    threadcount = atoi(argv[++argnext]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        goto err;
    }

    store = X509_STORE_new();
    if (store == NULL || !X509_STORE_set_default_paths(store)) {
        printf("Failed to create X509_STORE\n");
        goto err;
    }

    bio = BIO_new_file(cert, "rb");
    if (bio == NULL) {
        printf("Unable to load certificate\n");
        goto err;
    }
    x509 = PEM_read_bio_X509(bio, NULL, NULL, NULL);
    if (x509 == NULL) {
        printf("Failed to read certificate\n");
        goto err;
    }
    BIO_free(bio);
    bio = NULL;

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        goto err;
    }

    if (!perflib_run_multi_thread_test(do_x509storeissuer, threadcount, &duration)) {
        printf("Failed to run the test\n");
        goto err;
    }

    if (err) {
        printf("Error during test\n");
        goto err;
    }

    av = times[0];
    for (i = 1; i < threadcount; i++)
        av = ossl_time_add(av, times[i]);
    av = ossl_time_divide(av, threadcount);

    if (terse)
        printf("%ld\n", ossl_time2us(av));
    else
        printf("Average time per %d X509_STORE_CTX_get1_issuer() calls: %ldus\n",
               NUM_CALLS_PER_BLOCK, ossl_time2us(av));

    ret = EXIT_SUCCESS;
 err:
    X509_STORE_free(store);
    X509_free(x509);
    BIO_free(bio);
    OPENSSL_free(cert);
    OPENSSL_free(times);
    return ret;
}

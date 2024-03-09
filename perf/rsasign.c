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
#include <assert.h>
#include <openssl/pem.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_TEST         100000

int err = 0;
EVP_PKEY *rsakey = NULL;

static const char *rsakeypem =
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIBVwIBADANBgkqhkiG9w0BAQEFAASCAUEwggE9AgEAAkEAwmjwpbuKfvtBTAiQ\n"
    "U4OWjPVo0WM1UGGh9EJwgTnJm43l0HwL3GjmPBmToqhUYE6zfWi9jOpQkCSpDnIR\n"
    "1Pc18QIDAQABAkEAsKZmNFIK8IMhvBL0Ac7J19+OlOSOpzFv1eEhFWsK9FoNnsV/\n"
    "4Z4KlISNB+b7M5OJxYs4AutQIKr6zmlT7lk7OQIhAPj/LPWwkk+Ts2pBB64CokZ0\n"
    "C7GCeloMiPc3mCxsWbbnAiEAx+C6ham16nvvVUnYjoWSpNTuAhV61+FR0xKLk797\n"
    "iWcCIQCEy1KnFaxyVEtzd4so+q6g9HLoELZAID9L2ZKG3qJaMQIhAJFIU8tb9BKg\n"
    "SvJfXr0ZceHFs8pn+oZ4DJWzYSjfgdf5AiEAmk7Kt7Y8qPVJwb5bJL5CkoBxRwzS\n"
    "jHZXmRwpxC4tAFo=\n"
    "-----END PRIVATE KEY-----\n";

static const char *tbs = "0123456789abcdefghij"; /* Length of SHA1 digest */

static int threadcount;

static OSSL_TIME *times = NULL;

void do_rsasign(size_t num)
{
    int i;
    unsigned char buf[32];
    unsigned char sig[64];
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(rsakey, NULL);
    size_t siglen = sizeof(sig);
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_CALLS_PER_TEST / threadcount; i++) {
        if (EVP_PKEY_sign_init(ctx) <= 0
                || EVP_PKEY_sign(ctx, sig, &siglen, tbs, SHA_DIGEST_LENGTH) <= 0) {
            err = 1;
            break;
        }
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);

    EVP_PKEY_CTX_free(ctx);
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration;
    OSSL_TIME us;
    double avcalltime;
    int terse = 0;
    int argnext;
    BIO *membio = NULL;
    int rc = EXIT_FAILURE;
    size_t i;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: rsasign [--terse] threadcount\n");
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

    assert(strlen(tbs) == SHA_DIGEST_LENGTH);
    membio = BIO_new_mem_buf(rsakeypem, strlen(rsakeypem));
    if (membio == NULL) {
        printf("Failed to create internal BIO\n");
        return EXIT_FAILURE;
    }
    rsakey = PEM_read_bio_PrivateKey(membio, NULL, NULL, NULL);
    BIO_free(membio);
    if (rsakey == NULL) {
        printf("Failed to load the RSA key\n");
        goto out;
    }

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        goto out;
    }

    if (!perflib_run_multi_thread_test(do_rsasign, threadcount, &duration)) {
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

    avcalltime = (double)ossl_time2ticks(us) / (double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per RSA signature operation: %lfus\n",
               avcalltime);

    rc = EXIT_SUCCESS;

out:
    EVP_PKEY_free(rsakey);
    OPENSSL_free(times);
    return rc;
}

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

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  100
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

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

void do_rsasign(size_t num)
{
    int i;
    unsigned char buf[32];
    unsigned char sig[64];
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(rsakey, NULL);
    size_t siglen = sizeof(sig);

    for (i = 0; i < NUM_CALLS_PER_THREAD; i++) {
        if (EVP_PKEY_sign_init(ctx) <= 0
                || EVP_PKEY_sign(ctx, sig, &siglen, tbs, SHA_DIGEST_LENGTH) <= 0) {
            err = 1;
            break;
        }
    }
    EVP_PKEY_CTX_free(ctx);
}

int main(int argc, char *argv[])
{
    int threadcount;
    OSSL_TIME duration;
    uint64_t us;
    double avcalltime;
    int terse = 0;
    int argnext;
    BIO *membio = NULL;

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
        return EXIT_FAILURE;
    }

    if (!perflib_run_multi_thread_test(do_rsasign, threadcount, &duration)) {
        printf("Failed to run the test\n");
        EVP_PKEY_free(rsakey);
        return EXIT_FAILURE;
    }
    EVP_PKEY_free(rsakey);

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    avcalltime = (double)us / (NUM_CALL_BLOCKS_PER_THREAD * threadcount);

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per %d RSA signature operations: %lfus\n",
               NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}

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
#include <openssl/kdf.h>
#include <openssl/core_names.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_TEST         100000

OSSL_TIME *times;

int err = 0;

static int threadcount;

static OSSL_LIB_CTX *ctx = NULL;

#define ARRAY_SIZE(a)                               \
  ((sizeof(a) / sizeof(*(a))))

typedef enum {
    FETCH_MD = 0,
    FETCH_CIPHER,
    FETCH_KDF,
    FETCH_MAC,
    FETCH_RAND
} fetch_type_t;

struct fetch_data_entry {
    fetch_type_t ftype;
    const char *alg;
    const char *propq;
};

static struct fetch_data_entry fetch_entries[] = {
    {FETCH_MD, OSSL_DIGEST_NAME_SHA2_224, NULL},
    {FETCH_MD, OSSL_DIGEST_NAME_SHA2_256, NULL},
    {FETCH_MD, OSSL_DIGEST_NAME_SHA3_224, NULL},
    {FETCH_MD, OSSL_DIGEST_NAME_SHA3_256, NULL},
    {FETCH_CIPHER, OSSL_CIPHER_NAME_AES_128_GCM_SIV, NULL},
    {FETCH_CIPHER, OSSL_CIPHER_NAME_AES_192_GCM_SIV, NULL},
    {FETCH_CIPHER, OSSL_CIPHER_NAME_AES_256_GCM_SIV, NULL},
    {FETCH_KDF, OSSL_KDF_NAME_HKDF, NULL},
    {FETCH_KDF, OSSL_KDF_NAME_SCRYPT, NULL},
    {FETCH_KDF, OSSL_KDF_NAME_KRB5KDF, NULL},
    {FETCH_KDF, OSSL_KDF_NAME_KBKDF, NULL},
    {FETCH_MAC, OSSL_MAC_NAME_BLAKE2BMAC, NULL},
    {FETCH_MAC, OSSL_MAC_NAME_CMAC, NULL},
    {FETCH_MAC, OSSL_MAC_NAME_GMAC, NULL},
    {FETCH_MAC, OSSL_MAC_NAME_HMAC, NULL},
    {FETCH_MAC, OSSL_MAC_NAME_POLY1305, NULL},
    {FETCH_RAND, "CTR-DRBG", NULL}
};

void do_fetch(size_t num)
{
    OSSL_TIME start, end;
    size_t i, j;

    start = ossl_time_now();

    for (i = 0; i < NUM_CALLS_PER_TEST / threadcount; i++) {
        j = i % ARRAY_SIZE(fetch_entries);

        if (err == 1)
            return;

        switch (fetch_entries[j].ftype) {
        case FETCH_MD:
            EVP_MD *md = EVP_MD_fetch(ctx, fetch_entries[j].alg,
                                      fetch_entries[j].propq);
            if (md == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_entries[j].alg);
                err = 1;
                return;
            }
            EVP_MD_free(md);
            break;
        case FETCH_CIPHER:
            EVP_CIPHER *cph = EVP_CIPHER_fetch(ctx, fetch_entries[j].alg,
                                               fetch_entries[j].propq);
            if (cph == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_entries[j].alg);
                err = 1;
                return;
            }
            EVP_CIPHER_free(cph);
            break;
        case FETCH_KDF:
            EVP_KDF *kdf = EVP_KDF_fetch(ctx, fetch_entries[j].alg,
                                         fetch_entries[j].propq);
            if (kdf == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_entries[j].alg);
                err = 1;
                return;
            }
            EVP_KDF_free(kdf);
            break;
        case FETCH_MAC:
            EVP_MAC *mac = EVP_MAC_fetch(ctx, fetch_entries[j].alg,
                                         fetch_entries[j].propq);
            if (mac == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_entries[j].alg);
                err = 1;
                return;
            }
            EVP_MAC_free(mac);
            break;
        case FETCH_RAND:
            EVP_RAND *rnd = EVP_RAND_fetch(ctx, fetch_entries[j].alg,
                                           fetch_entries[j].propq);
            if (rnd == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_entries[j].alg);
                err = 1;
                return;
            }
            EVP_RAND_free(rnd);
            break;
        default:
            err = 1;
            return;
        }
    }
    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration;
    OSSL_TIME ttime;
    double av;
    int terse = 0;
    int argnext;
    size_t i;
    int rc = EXIT_FAILURE;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: %s [--terse] threadcount\n", argv[0]);
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

    ctx = OSSL_LIB_CTX_new();
    if (ctx == NULL)
        return EXIT_FAILURE;

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        return EXIT_FAILURE;
    }

    if (!perflib_run_multi_thread_test(do_fetch, threadcount, &duration)) {
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

    /*
     * EVP_PKEY_new_raw_public_key is pretty fast, running in
     * only a few us.  But ossl_time2us does integer division
     * and so because the average us computed above is less than
     * the value of OSSL_TIME_US, we wind up with truncation to
     * zero in the math.  Instead, manually do the division, casting
     * our values as doubles so that we compute the proper time
     */
    av = ((double)ossl_time2ticks(ttime) / (double)NUM_CALLS_PER_TEST) /(double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", av);
    else
        printf("Average time per fetch call: %lfus\n",
               av);

    rc = EXIT_SUCCESS;
out:
    OSSL_LIB_CTX_free(ctx);
    OPENSSL_free(times);
    return rc;
}

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
#include <libgen.h>
#include <unistd.h>
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/core_names.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_TEST         10000000

OSSL_TIME *times;

int err = 0;

static int threadcount;
size_t num_calls;

static OSSL_LIB_CTX *ctx = NULL;

#define ARRAY_SIZE(a)                               \
  ((sizeof(a) / sizeof(*(a))))

typedef enum {
    FETCH_MD = 0,
    FETCH_CIPHER,
    FETCH_KDF,
    FETCH_MAC,
    FETCH_RAND,
    FETCH_END
} fetch_type_t;

struct fetch_type_map {
    char *name;
    fetch_type_t id;
};

struct fetch_type_map type_map[] = {
    { "MD"    , FETCH_MD },
    { "CIPHER", FETCH_CIPHER },
    { "KDF"   , FETCH_KDF },
    { "MAC"   , FETCH_MAC },
    { "RAND"  , FETCH_RAND }
};

fetch_type_t exclusive_fetch_type = FETCH_END;
char *exclusive_fetch_alg = NULL;

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
    {FETCH_CIPHER, "AES-128-GCM", NULL},
    {FETCH_CIPHER, "AES-128-CBC", NULL},
    {FETCH_CIPHER, "AES-256-GCM", NULL},
    {FETCH_CIPHER, "AES-256-CBC", NULL},
    {FETCH_KDF, OSSL_KDF_NAME_HKDF, NULL},
#ifndef OPENSSL_NO_SCRYPT
    {FETCH_KDF, OSSL_KDF_NAME_SCRYPT, NULL},
#endif
    {FETCH_KDF, OSSL_KDF_NAME_KRB5KDF, NULL},
    {FETCH_KDF, OSSL_KDF_NAME_KBKDF, NULL},
#ifndef OPENSSL_NO_BLAKE2
    {FETCH_MAC, OSSL_MAC_NAME_BLAKE2BMAC, NULL},
#endif
#ifndef OPENSSL_NO_CMAC
    {FETCH_MAC, OSSL_MAC_NAME_CMAC, NULL},
#endif
    {FETCH_MAC, OSSL_MAC_NAME_GMAC, NULL},
    {FETCH_MAC, OSSL_MAC_NAME_HMAC, NULL},
#ifndef OPENSSL_NO_POLY1305
    {FETCH_MAC, OSSL_MAC_NAME_POLY1305, NULL},
#endif
};

void do_fetch(size_t num)
{
    OSSL_TIME start, end;
    size_t i, j;
    const char *fetch_alg = NULL;

    start = ossl_time_now();

    for (i = 0; i < num_calls / threadcount; i++) {
        /*
         * If we set a fetch type, always use that
         */
        if (exclusive_fetch_type == FETCH_END) {
            j = i % ARRAY_SIZE(fetch_entries);
            fetch_alg = fetch_entries[j].alg;
            j = fetch_entries[j].ftype;
        } else {
            j = exclusive_fetch_type;
            fetch_alg = exclusive_fetch_alg;
        }

        if (err == 1)
            return;

        switch (j) {
        case FETCH_MD: {
            EVP_MD *md = EVP_MD_fetch(ctx, fetch_alg,
                                      fetch_entries[j].propq);
            if (md == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_alg);
                err = 1;
                return;
            }
            EVP_MD_free(md);
            break;
        }
        case FETCH_CIPHER: {
            EVP_CIPHER *cph = EVP_CIPHER_fetch(ctx, fetch_alg,
                                               fetch_entries[j].propq);
            if (cph == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_alg);
                err = 1;
                return;
            }
            EVP_CIPHER_free(cph);
            break;
        }
        case FETCH_KDF: {
            EVP_KDF *kdf = EVP_KDF_fetch(ctx, fetch_alg,
                                         fetch_entries[j].propq);
            if (kdf == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_alg);
                err = 1;
                return;
            }
            EVP_KDF_free(kdf);
            break;
        }
        case FETCH_MAC: {
            EVP_MAC *mac = EVP_MAC_fetch(ctx, fetch_alg,
                                         fetch_entries[j].propq);
            if (mac == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_alg);
                err = 1;
                return;
            }
            EVP_MAC_free(mac);
            break;
        }
        case FETCH_RAND: {
            EVP_RAND *rnd = EVP_RAND_fetch(ctx, fetch_alg,
                                           fetch_entries[j].propq);
            if (rnd == NULL) {
                fprintf(stderr, "Failed to fetch %s\n", fetch_alg);
                err = 1;
                return;
            }
            EVP_RAND_free(rnd);
            break;
        }
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
    size_t i;
    int rc = EXIT_FAILURE;
    char *fetch_type = getenv("EVP_FETCH_TYPE");
    int opt;

    while ((opt = getopt(argc, argv, "t")) != -1) {
        switch (opt) {
        case 't':
            terse = 1;
            break;
        default:
            printf("Usage: %s [-t] threadcount\n", basename(argv[0]));
            printf("-t - terse output\n");
            return EXIT_FAILURE;
        }
    }

    if (fetch_type != NULL) {
        exclusive_fetch_alg = strstr(fetch_type, ":");
        if (exclusive_fetch_alg == NULL) {
            printf("Malformed EVP_FETCH_TYPE TYPE:ALG\n");
            return EXIT_FAILURE;
        }
        /* Split the string into a type and alg */
        *exclusive_fetch_alg = '\0';
        exclusive_fetch_alg++;
        for (i = 0; i < ARRAY_SIZE(type_map); i++) {
            if (!strcmp(fetch_type, type_map[i].name)) {
                exclusive_fetch_type = type_map[i].id;
                break;
            }
        }
        if (i == ARRAY_SIZE(type_map)) {
            printf("EVP_FETCH_TYPE is invalid\n");
            return EXIT_FAILURE;
        }
    }

    if (argv[optind] == NULL) {
        printf("threadcount is missing\n");
        return EXIT_FAILURE;
    }
    threadcount = atoi(argv[optind]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        return EXIT_FAILURE;
    }
    num_calls = NUM_CALLS_PER_TEST;
    if (NUM_CALLS_PER_TEST % threadcount > 0) /* round up */
        num_calls += threadcount - NUM_CALLS_PER_TEST % threadcount;

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
     * EVP_fetch_* calls are pretty fast, running in
     * only a few us.  But ossl_time2us does integer division
     * and so because the average us computed above is less than
     * the value of OSSL_TIME_US, we wind up with truncation to
     * zero in the math.  Instead, manually do the division, casting
     * our values as doubles so that we compute the proper time
     */
    av = ((double)ossl_time2ticks(ttime) / num_calls) /(double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", av);
    else
        printf("Average time per fetch call: %lfus\n", av);

    rc = EXIT_SUCCESS;
out:
    OSSL_LIB_CTX_free(ctx);
    OPENSSL_free(times);
    return rc;
}

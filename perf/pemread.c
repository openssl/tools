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
#include <openssl/pem.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  100
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

int err = 0;

const char *pemdataraw[] = {
    "-----BEGIN RSA PRIVATE KEY-----\n",
    "MIIBOgIBAAJBAMFcGsaxxdgiuuGmCkVImy4h99CqT7jwY3pexPGcnUFtR2Fh36Bp\n",
    "oncwtkZ4cAgtvd4Qs8PkxUdp6p/DlUmObdkCAwEAAQJAUR44xX6zB3eaeyvTRzms\n",
    "kHADrPCmPWnr8dxsNwiDGHzrMKLN+i/HAam+97HxIKVWNDH2ba9Mf1SA8xu9dcHZ\n",
    "AQIhAOHPCLxbtQFVxlnhSyxYeb7O323c3QulPNn3bhOipElpAiEA2zZpBE8ZXVnL\n",
    "74QjG4zINlDfH+EOEtjJJ3RtaYDugvECIBtsQDxXytChsRgDQ1TcXdStXPcDppie\n",
    "dZhm8yhRTTBZAiAZjE/U9rsIDC0ebxIAZfn3iplWh84yGB3pgUI3J5WkoQIhAInE\n",
    "HTUY5WRj5riZtkyGnbm3DvF+1eMtO2lYV+OuLcfE\n",
    "-----END RSA PRIVATE KEY-----\n",
    NULL
};

void do_pemread(size_t num)
{
    EVP_PKEY *key;
    BIO *pem;
    int i;
    char *pemdata;
    size_t len;

    pemdata = perflib_glue_strings(pemdataraw, &len);
    if (pemdata == NULL) {
        printf("Cannot create PEM data\n");
        err = 1;
        return;
    }

    pem = BIO_new_mem_buf(pemdata, len);
    if (pem == NULL) {
        printf("Cannot create mem BIO\n");
        err = 1;
        return;
    }

    /*
     * Technically this includes the EVP_PKEY_free() in the timing - but I
     * think we can live with that
     */
    for (i = 0; i < NUM_CALLS_PER_THREAD; i++) {
        key = PEM_read_bio_PrivateKey(pem, NULL, NULL, NULL);
        if (key == NULL) {
            printf("Failed to create key: %d\n", i);
            err = 1;
            BIO_free(pem);
            return;
        }
        EVP_PKEY_free(key);
        BIO_reset(pem);
    }

    BIO_free(pem);
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
        printf("Usage: pemread [--terse] threadcount\n");
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

    if (!perflib_run_multi_thread_test(do_pemread, threadcount, &duration)) {
        printf("Failed to run the test\n");
        return EXIT_FAILURE;
    }

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    avcalltime = (double)us / (NUM_CALL_BLOCKS_PER_THREAD * threadcount);

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per %d PEM_read_bio_PrivateKey() calls: %lfus\n",
               NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}

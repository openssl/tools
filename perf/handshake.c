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

#define NUM_HANDSHAKES_PER_RUN        100000

int err = 0;

static SSL_CTX *sctx = NULL, *cctx = NULL;

OSSL_TIME *times;

static int threadcount;

static void do_handshake(size_t num)
{
    SSL *clientssl = NULL, *serverssl = NULL;
    int ret = 1;
    int i;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_HANDSHAKES_PER_RUN / threadcount; i++) {
        ret = perflib_create_ssl_objects(sctx, cctx, &serverssl, &clientssl,
                                         NULL, NULL);
        ret &= perflib_create_ssl_connection(serverssl, clientssl,
                                             SSL_ERROR_NONE);
        perflib_shutdown_ssl_connection(serverssl, clientssl);
        serverssl = clientssl = NULL;
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);

    if (!ret)
        err = 1;
}

int main(int argc, char *argv[])
{
    double persec;
    OSSL_TIME duration, ttime;
    uint64_t us;
    double avcalltime;
    char *cert;
    char *privkey;
    int ret = EXIT_FAILURE;
    int i;
    int argnext;
    int terse = 0;

    if ((argc != 3 && argc != 4)
            || (argc == 4 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: handshake [--terse] certsdir threadcount\n");
        return EXIT_FAILURE;
    }

    if (argc == 4) {
        terse = 1;
        argnext = 2;
    } else {
        argnext = 1;
    }

    cert = perflib_mk_file_path(argv[argnext], "servercert.pem");
    privkey = perflib_mk_file_path(argv[argnext], "serverkey.pem");
    if (cert == NULL || privkey == NULL) {
        printf("Failed to allocate cert/privkey\n");
        goto err;
    }

    threadcount = atoi(argv[++argnext]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        goto err;
    }

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        goto err;
    }

    if (!perflib_create_ssl_ctx_pair(TLS_server_method(), TLS_client_method(),
                                     0, 0, &sctx, &cctx, cert, privkey)) {
        printf("Failed to create SSL_CTX pair\n");
        goto err;
    }

    if (!perflib_run_multi_thread_test(do_handshake, threadcount, &duration)) {
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

    avcalltime = ((double)ossl_time2ticks(ttime) / (double)NUM_HANDSHAKES_PER_RUN) / (double)OSSL_TIME_US;
    persec = ((NUM_HANDSHAKES_PER_RUN * OSSL_TIME_SECOND)
             / (double)ossl_time2ticks(duration));

    if (terse) {
        printf("%lf\n", avcalltime);
        printf("%lf\n", persec);
    } else {
        printf("Average time per handshake: %lfus\n", avcalltime);
        printf("Handshakes per second: %lf\n", persec);
    }

    ret = EXIT_SUCCESS;
 err:
    OPENSSL_free(cert);
    OPENSSL_free(privkey);
    OPENSSL_free(times);
    SSL_CTX_free(sctx);
    SSL_CTX_free(cctx);
    return ret;
}

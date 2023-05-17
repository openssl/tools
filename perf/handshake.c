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
#include <openssl/ssl.h>
#include "perflib/perflib.h"

#define NUM_HANDSHAKES_PER_THREAD         1000

int err = 0;

static SSL_CTX *sctx = NULL, *cctx = NULL;

OSSL_TIME *times;

static void do_handshake(size_t num)
{
    SSL *clientssl = NULL, *serverssl = NULL;
    int ret = 1;
    int i;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < NUM_HANDSHAKES_PER_THREAD; i++) {
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
    int threadcount;
    double persec;
    OSSL_TIME duration, av;
    uint64_t us;
    double avcalltime;
    char *cert;
    char *privkey;
    int ret = EXIT_FAILURE;
    int i;

    if (argc != 3) {
        printf("Usage: handshake certsdir threadcount\n");
        return EXIT_FAILURE;
    }

    threadcount = atoi(argv[2]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        return EXIT_FAILURE;
    }

    cert = perflib_mk_file_path(argv[1], "servercert.pem");
    privkey = perflib_mk_file_path(argv[1], "serverkey.pem");
    if (cert == NULL || privkey == NULL) {
        printf("Failed to allocate cert/privkey\n");
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

    av = times[0];
    for (i = 1; i < threadcount; i++)
        av = ossl_time_add(av, times[i]);
    av = ossl_time_divide(av, NUM_HANDSHAKES_PER_THREAD * threadcount);

    persec = ((NUM_HANDSHAKES_PER_THREAD * threadcount * OSSL_TIME_SECOND)
             / (double)ossl_time2ticks(duration));

    printf("Average time per handshake: %ldus\n", ossl_time2us(av));
    printf("Handshakes per second: %lf\n", persec);

    ret = EXIT_SUCCESS;
 err:
    OPENSSL_free(cert);
    OPENSSL_free(privkey);
    OPENSSL_free(times);
    SSL_CTX_free(sctx);
    SSL_CTX_free(cctx);
    return ret;
}

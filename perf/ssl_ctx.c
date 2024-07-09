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
#include <unistd.h>
#include <openssl/ssl.h>
#include "perflib/perflib.h"

#define NUM_CTX_PER_RUN        100000

int err = 0;

OSSL_TIME *times;
static char *certpath = NULL;
static char *keypath = NULL;
static char *storepath = NULL;

static int threadcount;
static int adj_ctx_per_run = 0;

typedef enum {
    OP_SERVER,
    OP_CLIENT
} op_mode;

op_mode mode = OP_SERVER;

static void do_create_ctx(size_t num)
{
    int i;
    SSL_CTX *ctx = NULL;
    OSSL_TIME start, end;

    start = ossl_time_now();

    for (i = 0; i < adj_ctx_per_run / threadcount; i++) {
        ctx = SSL_CTX_new(mode == OP_SERVER ? TLS_server_method() :
                                              TLS_client_method());
        if (ctx == NULL)
            goto out;
        if (mode == OP_SERVER) {
            if ((SSL_CTX_use_certificate_file(ctx, certpath,
                                              SSL_FILETYPE_PEM) != 1) ||
                (SSL_CTX_use_PrivateKey_file(ctx, keypath,
                                             SSL_FILETYPE_PEM) != 1)) {
                err = 1;
                goto out;
            }
        } else {
            if (SSL_CTX_load_verify_dir(ctx, storepath) != 1) {
                err = 1;
                goto out;
            }
        }
        SSL_CTX_free(ctx);
    }

out:
    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);
}

static void usage(char *name)
{
    fprintf(stderr, "usage\n");
    fprintf(stderr, "%s [-m <server|client>] [-c <cert>] [-k <key>] [-s <store>] <threadcount> \n", name);
    fprintf(stderr, "-m <server|client> - create a client or server method in context\n");
    fprintf(stderr, "-c <cert> - path to certificate for server context\n");
    fprintf(stderr, "-k <key> - path to key for server context\n");
    fprintf(stderr, "-s <store> - path to cert store for client context\n");
}

int main(int argc, char *argv[])
{
    OSSL_TIME duration, ttime;
    uint64_t us;
    double avcalltime;
    int ret = EXIT_FAILURE;
    int i;
    int terse = 0;
    int ch = 0;

    while ((ch = getopt(argc, argv, "tm:c:k:s:")) != -1) {
        switch(ch) {
        case 'm':
            if (!strcmp(optarg, "server")) {
                mode = OP_SERVER;
            } else if (!strcmp(optarg, "client")) {
                mode = OP_CLIENT;
            } else {
                printf("-m must select one of client|server\n");
                usage(argv[0]);
            }
            break;
        case 'c':
            certpath = optarg;
            break;
        case 'k':
            keypath = optarg;
            break;
        case 's':
            storepath = optarg;
            break;
        case 't':
            terse = 1;
            break;
        default:
            usage(argv[0]);
            exit(1);
        }
    }

    if (argv[optind] == NULL) {
        printf("Missing threadcount argument\n");
        usage(argv[0]);
        goto err;
    }

    threadcount = atoi(argv[optind]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        goto err;
    }

    /* Adjust the number of iterations so we divide evenly among threads */
    adj_ctx_per_run = (NUM_CTX_PER_RUN / threadcount) * threadcount;

    if (mode == OP_SERVER) {
        if (certpath == NULL | keypath == NULL) {
            printf("server mode requires both -c and -k options\n");
            usage(argv[0]);
            goto err;
        }
    } else {
        if (storepath == NULL) {
            printf("client mode requires -s option\n");
            usage(argv[0]);
            goto err;
        }
    }

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        goto err;
    }

    if (!perflib_run_multi_thread_test(do_create_ctx, threadcount, &duration)) {
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

    avcalltime = ((double)ossl_time2ticks(ttime) / (double)adj_ctx_per_run) / (double)OSSL_TIME_US;

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per ssl ctx setup: %lfus\n", avcalltime);

    ret = EXIT_SUCCESS;
 err:
    OPENSSL_free(times);
    return ret;
}

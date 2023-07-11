/*
 * Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#ifndef OSSL_PERFLIB_PERFLIB_H
# define OSSL_PERFLIB_PERFLIB_H
# pragma once

#include <stdlib.h>
#include <openssl/ssl.h>
#include <openssl/bio.h>
#include "perflib/time.h"

# if defined(_WIN32)

#  include <windows.h>

typedef HANDLE thread_t;

# else

#  include <pthread.h>

typedef pthread_t thread_t;

# endif

int perflib_run_multi_thread_test(void (*f)(size_t), size_t threadcount,
                                  OSSL_TIME *duration);
char *perflib_mk_file_path(const char *dir, const char *file);
char *perflib_glue_strings(const char *list[], size_t *out_len);

int perflib_create_ssl_ctx_pair(const SSL_METHOD *sm, const SSL_METHOD *cm,
                                int min_proto_version, int max_proto_version,
                                SSL_CTX **sctx, SSL_CTX **cctx, char *certfile,
                                char *privkeyfile);
int perflib_create_ssl_objects(SSL_CTX *serverctx, SSL_CTX *clientctx,
                               SSL **sssl, SSL **cssl, BIO *s_to_c_fbio,
                               BIO *c_to_s_fbio);
int perflib_create_bare_ssl_connection(SSL *serverssl, SSL *clientssl, int want);
int perflib_create_ssl_connection(SSL *serverssl, SSL *clientssl, int want);
void perflib_shutdown_ssl_connection(SSL *serverssl, SSL *clientssl);

#endif

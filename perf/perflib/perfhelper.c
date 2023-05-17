/*
 * Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include <openssl/crypto.h>
#include "perflib/perflib.h"

int perflib_run_multi_thread_test(void (*f)(void), size_t threadcount,
                                  OSSL_TIME *duration)
{
    OSSL_TIME start, end;
    thread_t *threads;
    size_t i;

    threads = OPENSSL_malloc(sizeof(*threads) * threadcount);
    if (threads == NULL)
        return 0;

    start = ossl_time_now();

    for (i = 0; i < threadcount; i++)
        perflib_run_thread(&threads[i], f);

    for (i = 0; i < threadcount; i++)
        perflib_wait_for_thread(threads[i]);

    end = ossl_time_now();
    OPENSSL_free(threads);

    *duration = ossl_time_subtract(end, start);

    return 1;
}

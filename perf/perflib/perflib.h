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
#include "perflib/time.h"

# if defined(_WIN32)

#  include <windows.h>

typedef HANDLE thread_t;

# else

#  include <pthread.h>

typedef pthread_t thread_t;

# endif

int perflib_run_thread(thread_t *t, void (*f)(void));
int perflib_wait_for_thread(thread_t thread);
int perflib_run_multi_thread_test(void (*f)(void), size_t threadcount,
                                  OSSL_TIME *duration);

#endif

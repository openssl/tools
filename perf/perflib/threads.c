/*
 * Copyright 2021 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include "perflib/perflib.h"

struct thread_arg_st {
    void (*func)(size_t num);
    size_t num;
};

#if defined(_WIN32)

static DWORD WINAPI thread_run(LPVOID varg)
{
    struct thread_arg_st *arg = varg;

    arg->func(arg->num);

    return 0;
}

int perflib_run_thread(thread_t *t, struct thread_arg_st *arg)
{
    *t = CreateThread(NULL, 0, thread_run, arg, 0, NULL);
    return *t != NULL;
}

int perflib_wait_for_thread(thread_t thread)
{
    return WaitForSingleObject(thread, INFINITE) == 0;
}

#else

static void *thread_run(void *varg)
{
    struct thread_arg_st *arg = varg;

    arg->func(arg->num);

    return NULL;
}

int perflib_run_thread(thread_t *t, struct thread_arg_st *arg)
{
    return pthread_create(t, NULL, thread_run, arg) == 0;
}

int perflib_wait_for_thread(thread_t thread)
{
    return pthread_join(thread, NULL) == 0;
}

#endif

int perflib_run_multi_thread_test(void (*f)(size_t), size_t threadcount,
                                  OSSL_TIME *duration)
{
    OSSL_TIME start, end;
    thread_t *threads;
    size_t i;
    struct thread_arg_st *args;

    threads = OPENSSL_malloc(sizeof(*threads) * threadcount);
    if (threads == NULL)
        return 0;

    args = OPENSSL_malloc(sizeof(*args) * threadcount);
    if (args == NULL) {
        OPENSSL_free(threads);
        return 0;
    }

    start = ossl_time_now();

    for (i = 0; i < threadcount; i++) {
        args[i].func = f;
        args[i].num = i;
        perflib_run_thread(&threads[i], &args[i]);
    }

    for (i = 0; i < threadcount; i++)
        perflib_wait_for_thread(threads[i]);

    end = ossl_time_now();
    OPENSSL_free(threads);
    OPENSSL_free(args);

    *duration = ossl_time_subtract(end, start);

    return 1;
}

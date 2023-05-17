/*
 * Copyright 2021 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include "perflib/perflib.h"

#if defined(_WIN32)

static DWORD WINAPI thread_run(LPVOID arg)
{
    void (*f)(void);

    *(void **) (&f) = arg;

    f();
    return 0;
}

int perflib_run_thread(thread_t *t, void (*f)(void))
{
    *t = CreateThread(NULL, 0, thread_run, *(void **) &f, 0, NULL);
    return *t != NULL;
}

int perflib_wait_for_thread(thread_t thread)
{
    return WaitForSingleObject(thread, INFINITE) == 0;
}

#else

static void *thread_run(void *arg)
{
    void (*f)(void);

    *(void **) (&f) = arg;

    f();
    return NULL;
}

int perflib_run_thread(thread_t *t, void (*f)(void))
{
    return pthread_create(t, NULL, thread_run, *(void **) &f) == 0;
}

int perflib_wait_for_thread(thread_t thread)
{
    return pthread_join(thread, NULL) == 0;
}

#endif

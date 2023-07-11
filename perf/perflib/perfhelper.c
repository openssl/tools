/*
 * Copyright 2023 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include <string.h>
#include <openssl/crypto.h>
#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/ssl.h>
#include "perflib/perflib.h"

char *perflib_mk_file_path(const char *dir, const char *file)
{
    const char *sep = "/";
    size_t dirlen = dir != NULL ? strlen(dir) : 0;
    size_t len = dirlen + strlen(sep) + strlen(file) + 1;
    char *full_file = OPENSSL_zalloc(len);

    if (full_file != NULL) {
        if (dir != NULL && dirlen > 0) {
            OPENSSL_strlcpy(full_file, dir, len);
            OPENSSL_strlcat(full_file, sep, len);
        }
        OPENSSL_strlcat(full_file, file, len);
    }

    return full_file;
}

/*
 * Glue an array of strings together and return it as an allocated string.
 * Optionally return the whole length of this string in |out_len|
 */
char *perflib_glue_strings(const char *list[], size_t *out_len)
{
    size_t len = 0;
    char *p, *ret;
    int i;

    for (i = 0; list[i] != NULL; i++)
        len += strlen(list[i]);

    if (out_len != NULL)
        *out_len = len;

    ret = p = OPENSSL_malloc(len + 1);
    if (p == NULL)
        return NULL;

    for (i = 0; list[i] != NULL; i++)
        p += strlen(strcpy(p, list[i]));

    return ret;
}

/*
 * Copyright 2024 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include <string.h>

/*
 * windows variant of basename(3). works on ASCIIZ only.
 * simple and perhaps naive implementation too.
 */
const char *
basename(const char *path)
{
	const char *rv;

	rv = (const char *)strrchr(path, '\\');
	if (rv != NULL) {
		rv++;
		if (*rv == '\0')
			rv = path;
	}

	return (rv);
}

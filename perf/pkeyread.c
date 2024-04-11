/*
 * Copyright 2024 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the Apache License 2.0 (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <openssl/x509.h>
#include <openssl/evp.h>
#include "perflib/perflib.h"

#define NUM_CALLS_PER_BLOCK         1000
#define NUM_CALL_BLOCKS_PER_RUN     100
#define NUM_CALLS_PER_RUN           (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_RUN)

#define NUM_LOOPS		256

static int threadcount;
static int fail = 0;

/*
 * PKEY_INFO is der representation of ASN.1 form for private key info.
 * See RFC 5208 Section 5 'Private-Key information Syntax'
 */
static const char PKEY_INFO_HDR[] = {
    0x30, 0x2e,          /* SEQUENCE(3 elem) (46 bytes) */
    0x02, 0x01, 0x00,    /*   INTEGER 0	version */
    /*
     * Private Key Algorithm Identifier. We use ECDH curve X25519.
     * What follows here is BER representation of X25519 OID (1.3.101.110)
     * see RFC 8410, Section 9 ASN.1 Module.
     */
    0x30, 0x05,          /*   SEQUENCE(1 elem) (5 bytes) */
    0x06, 0x03,          /*     OBJECT IDENTIFIER (3 bytes) */
    0x2b, 0x65, 0x6e,    /*       OID 1.3.101.110 [ 1*40+3, 101, 110 ] */
    0x04, 0x22,          /*   OCTET STRING(1 elem) (nested) */
    0x04, 0x20           /*     OCTET STRING(32 bytes) */
    /* key follows here */
};

#define X25519_PRIVATE_KEY_SZ	32	/* 32 bytes 256 bits */
#define X25519_PUBLIC_KEY_SZ	32	/* 32 bytes 256 bits */
#define PKEY_INFO_HDR_SZ	sizeof(PKEY_INFO_HDR)
#define	PKEY_DER_SZ		(PKEY_INFO_HDR_SZ + X25519_PRIVATE_KEY_SZ)

static int
pkcs8_decode(const unsigned char *pdata)
{
    unsigned char pkey_der[PKEY_DER_SZ];
    const unsigned char *pder = (const unsigned char *)pkey_der;
    unsigned char *priv_data = pkey_der + PKEY_INFO_HDR_SZ;
    const unsigned char *pk_buf = NULL;
    int pk_buf_len;
    PKCS8_PRIV_KEY_INFO *pkey_info8 = NULL;
    EVP_PKEY *pkey = NULL;
    X509_PUBKEY *key = NULL;
    int err = 1;


    memcpy(pkey_der, PKEY_INFO_HDR, PKEY_INFO_HDR_SZ);
    memcpy(priv_data, pdata, X25519_PRIVATE_KEY_SZ);

    pkey_info8 = d2i_PKCS8_PRIV_KEY_INFO(NULL, &pder, PKEY_DER_SZ);
    if (pkey_info8 == 0)
	goto error;

    pkey = EVP_PKCS82PKEY(pkey_info8);
    if (key == NULL)
	goto error;

    if (X509_PUBKEY_set(&key, pkey) == 0)
	goto error;

    if (X509_PUBKEY_get0_param(NULL, &pk_buf, &pk_buf_len, NULL, key) == 0)
	goto error;

    err = (pk_buf == NULL) || (pk_buf_len != X25519_PUBLIC_KEY_SZ);

error:
    X509_PUBKEY_free(key);
    EVP_PKEY_free(pkey);
    PKCS8_PRIV_KEY_INFO_free(pkey_info8);

    return err;
}

static int 
pkcs8_decode_batch(void)
{
    unsigned int i, j;
    unsigned char pkey[X25519_PRIVATE_KEY_SZ];

    memset(pkey, 0, X25519_PRIVATE_KEY_SZ);
    for (i = 0; i < NUM_LOOPS; i++) {
	pkey[0] = i;
	for(j = 0 ; j < NUM_LOOPS; j++) {
	    pkey[1] = j;
	    if (pkcs8_decode(pkey) == 1) {
		return 0;
	    }
	}
    }

    return 1;
}

static void
do_pkcs8_decode(size_t unused)
{
    int i;
    int err = 0;

    for (i = 0; err == 0 && i < NUM_CALLS_PER_RUN / threadcount; i++)
        err = pkcs8_decode_batch();

    if (err)
	fail = 1;
}

int
main(int argc, const char * const argv[])
{
    OSSL_TIME duration;
    uint64_t us;
    double avcalltime;
    int terse = 0;
    int argnext;

    if ((argc != 2 && argc != 3)
                || (argc == 3 && strcmp("--terse", argv[1]) != 0)) {
        printf("Usage: pemread [--terse] threadcount\n");
        return EXIT_FAILURE;
    }

    if (argc == 3) {
        terse = 1;
        argnext = 2;
    } else {
        argnext = 1;
    }

    threadcount = atoi(argv[argnext]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        return EXIT_FAILURE;
    }

    if (!perflib_run_multi_thread_test(do_pkcs8_decode, threadcount, &duration)) {
        printf("Failed to run the test\n");
        return EXIT_FAILURE;
    }

    if (fail) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(duration);

    avcalltime = (double)us / NUM_CALL_BLOCKS_PER_RUN;

    if (terse)
        printf("%lf\n", avcalltime);
    else
        printf("Average time per %d pkcs8_decode_batch() calls: %lfus\n",
               NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}

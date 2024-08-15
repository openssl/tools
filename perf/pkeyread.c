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
#include <openssl/pem.h>
#include <openssl/evp.h>
#include <openssl/x509.h>
#include <openssl/crypto.h>
#include "perflib/perflib.h"

/* run 'make regen_key_samples' if header file is missing */
#include "keys.h"

#define NUM_CALLS_PER_TEST         10000

size_t num_calls;
static OSSL_TIME *times = NULL;

int err = 0;

static int threadcount;

static unsigned int sample_id;

static void do_pemread(size_t num)
{
    const char *keydata;
    size_t keydata_sz;
    EVP_PKEY *key;
    BIO *pem;
    size_t i;
    size_t len;
    OSSL_TIME start, end;

    if (sample_id >= SAMPLE_ALL) {
        fprintf(stderr, "%s no sample key set for test\n", __func__);
        err = 1;
        return;
    }

    keydata = sample_keys[sample_id][FORMAT_PEM];
    keydata_sz = sample_key_sizes[sample_id][FORMAT_PEM];
    pem = BIO_new_mem_buf(keydata, keydata_sz);

    if (pem == NULL) {
        fprintf(stderr, "%s Cannot create mem BIO [%s PEM]\n",
                __func__, sample_names[sample_id]);
        err = 1;
        return;
    }

    start = ossl_time_now();

    /*
     * Technically this includes the EVP_PKEY_free() in the timing - but I
     * think we can live with that
     */
    for (i = 0; i < num_calls / threadcount; i++) {
        key = PEM_read_bio_PrivateKey(pem, NULL, NULL, NULL);
        if (key == NULL) {
            fprintf(stderr, "Failed to create key: %llu [%s PEM]\n",
                    (unsigned long long)i,
                    sample_names[sample_id]);
            err = 1;
            BIO_free(pem);
            return;
        }
        EVP_PKEY_free(key);
        BIO_reset(pem);
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);

    BIO_free(pem);
}

static int sample_id_to_evp(int sample_id)
{
    int rv;

    if ((sample_id < 0) || (sample_id >= SAMPLE_ALL))
        return EVP_PKEY_NONE;

    return evp_pkey_tab[sample_id];
}

static void do_derread(size_t num)
{
    const unsigned char *keydata;
    size_t keydata_sz;
    const unsigned char *pk_buf = NULL;
    int pk_buf_len;
    EVP_PKEY *pkey = NULL;
    int i;
    OSSL_TIME start, end;

    if (sample_id >= SAMPLE_ALL) {
        fprintf(stderr, "%s no sample key set for test\n", __func__);
        err = 1;
        return;
    }


    start = ossl_time_now();

    for (i = 0; i < num_calls / threadcount && err == 0; i++) {
        keydata = (const unsigned char *)sample_keys[sample_id][FORMAT_DER];
        keydata_sz = sample_key_sizes[sample_id][FORMAT_DER];
        pkey = d2i_PrivateKey(sample_id_to_evp(sample_id), NULL,
                          &keydata, keydata_sz);
        if (pkey == NULL) {
            fprintf(stderr, "%s pkey is NULL [%s DER]\n",
                    __func__, sample_names[sample_id]);
            err = 1;
            goto error;
        }
error:
        EVP_PKEY_free(pkey);
        pkey = NULL;
    }

    end = ossl_time_now();
    times[num] = ossl_time_subtract(end, start);
}

static int sample_name_to_id(const char *sample_name)
{
    int i = 0;

    while (sample_names[i] != NULL) {
        if (strcasecmp(sample_names[i], sample_name) == 0)
            break;
        i++;
    }

    return i;
}

static int format_name_to_id(const char *format_name)
{
    int i = 0;

    while (format_names[i] != NULL) {
        if (strcasecmp(format_names[i], format_name) == 0)
            break;
        i++;
    }

    return i;
}

static double get_avcalltime(void)
{
    int i;
    OSSL_TIME t;
    double avcalltime;

    memset(&t, 0, sizeof(t));
    for (i = 0; i < threadcount; i++)
        t = ossl_time_add(t, times[i]);
    avcalltime = (double)ossl_time2ticks(t) / num_calls;

    avcalltime =  avcalltime / (double)OSSL_TIME_US;

    return avcalltime;
}

static void report_result(int key_id, int format_id, int terse)
{
    if (err) {
	fprintf(stderr, "Error during test of %s in %s format\n",
	        sample_names[key_id], format_names[format_id]);
	exit(EXIT_FAILURE);
    }

    if (terse)
	printf("[%s %s] %lfus\n", sample_names[key_id],
	       format_names[format_id], get_avcalltime());
    else
	printf("Average time per %s(%s) call: %lfus\n",
	       format_names[format_id], sample_names[key_id], get_avcalltime());
}

static void usage(char * const argv[])
{
    const char **key_name = sample_names;
    const char **format_name = format_names;

    fprintf(stderr, "%s -k key_name -f format_name [-t] terse threadcount\n"
        "\twhere key_name is one of these: ", argv[0]);
    fprintf(stderr, "%s", *key_name);
    do {
        key_name++;
        if (*key_name == NULL)
            fprintf(stderr, "\n");
        else
            fprintf(stderr, ", %s", *key_name);
    } while (*key_name != NULL);

    fprintf(stderr, "\tformat_name is one of these: %s", *format_name);
    do {
        format_name++;
        if (*format_name == NULL)
            fprintf(stderr, "\n");
        else
            fprintf(stderr, ", %s", *format_name);
    } while (*format_name != NULL);
}

int main(int argc, char * const argv[])
{
    OSSL_TIME duration;
    int ch, i;
    int key_id, key_id_min, key_id_max, k;
    int format_id, format_id_min, format_id_max, f;
    int terse = 0;
    char *key = NULL;
    char *key_format = NULL;
    int kf;
    void (*do_f[2])(size_t) = {
        do_pemread,
        do_derread
    };
    const char *fname[] = {
        "PEM_read_bio_PrivateKey",
        "X509_PUBKEY_get0_param"
    };

    key_id = SAMPLE_INVALID;
    format_id = FORMAT_INVALID;

    while ((ch = getopt(argc, argv, "k:f:t")) != -1) {
        switch (ch) {
        case 'k':
            key = optarg;
            break;
        case 'f':
            key_format = optarg;
            break;
        case 't':
            terse = 1;
            break;
        }
    }

    if (argv[optind] == NULL) {
        fprintf(stderr, "Missing threadcount argument\n");
        usage(argv);
        return EXIT_FAILURE;
    }

    threadcount = atoi(argv[optind]);
    if (threadcount < 1) {
        fprintf(stderr, "threadcount must be > 0\n");
        usage(argv);
        return EXIT_FAILURE;
    }

    if (key != NULL) {
        key_id = sample_name_to_id(key);
        if (key_id == SAMPLE_INVALID) {
            fprintf(stderr, "Unknown key name (%s)\n", key);
            usage(argv);
            return EXIT_FAILURE;
        }
    }

    if (key_format != NULL) {
        format_id = format_name_to_id(key_format);
        if (format_id == FORMAT_INVALID) {
            fprintf(stderr, "Unknown key format (%s)\n", key_format);
            usage(argv);
            return EXIT_FAILURE;
        }
    }

    if (key_format == NULL) {
        fprintf(stderr, "option -f is missing\n");
        usage(argv);
        return EXIT_FAILURE;
    }

    if (key == NULL) {
        fprintf(stderr, "option -k is missing\n");
        usage(argv);
        return EXIT_FAILURE;
    }

    if (threadcount < 1) {
        fprintf(stderr, "threadcount must be > 0, use option -t 1\n");
        usage(argv);
        return EXIT_FAILURE;
    }
    num_calls = NUM_CALLS_PER_TEST;
    if (NUM_CALLS_PER_TEST % threadcount > 0) /* round up */
        num_calls += threadcount - NUM_CALLS_PER_TEST % threadcount;

    times = OPENSSL_malloc(sizeof(OSSL_TIME) * threadcount);
    if (times == NULL) {
        printf("Failed to create times array\n");
        return EXIT_FAILURE;
    }

    if (key_id == SAMPLE_ALL) {
        key_id_min = 0;
        key_id_max = SAMPLE_ALL;
    } else {
        key_id_min = key_id;
        key_id_max = key_id + 1;
    }
    if (format_id == FORMAT_ALL) {
        format_id_min = 0;
        format_id_max = FORMAT_ALL;
    } else {
        format_id_min = format_id;
        format_id_max = format_id + 1;
    }
    /* run samples/formats as appropriate */
    for (k = key_id_min; k < key_id_max; k++) {
        sample_id = k;
        for (f = format_id_min; f < format_id_max; f++) {
            if (!perflib_run_multi_thread_test(do_f[f], threadcount, &duration)) {
                fprintf(stderr, "Failed to run the test %s in %s format]\n",
                        sample_names[k], format_names[f]);
                return EXIT_FAILURE;
            }
            report_result(k, f, terse);
        }
    }

    return EXIT_SUCCESS;
}

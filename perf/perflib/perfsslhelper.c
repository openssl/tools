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

int perflib_create_ssl_ctx_pair(const SSL_METHOD *sm,
                                const SSL_METHOD *cm, int min_proto_version,
                                int max_proto_version, SSL_CTX **sctx,
                                SSL_CTX **cctx, char *certfile,
                                char *privkeyfile)
{
    SSL_CTX *serverctx = NULL;
    SSL_CTX *clientctx = NULL;

    if (sctx != NULL) {
        if (*sctx != NULL)
            serverctx = *sctx;
        else if ((serverctx = SSL_CTX_new(sm)) == NULL)
            goto err;
    }

    if (cctx != NULL) {
        if (*cctx != NULL)
            clientctx = *cctx;
        else if ((clientctx = SSL_CTX_new(cm)) == NULL)
            goto err;
    }

    if (serverctx != NULL
            && ((min_proto_version > 0
                 && !SSL_CTX_set_min_proto_version(serverctx,
                                                   min_proto_version))
                || (max_proto_version > 0
                    && !SSL_CTX_set_max_proto_version(serverctx,
                                                      max_proto_version))))
        goto err;

    if (clientctx != NULL
        && ((min_proto_version > 0
             && !SSL_CTX_set_min_proto_version(clientctx,
                                               min_proto_version))
            || (max_proto_version > 0
                && !SSL_CTX_set_max_proto_version(clientctx,
                                                  max_proto_version))))
        goto err;

    if (serverctx != NULL && certfile != NULL && privkeyfile != NULL) {
        if (SSL_CTX_use_certificate_file(serverctx, certfile,
                                         SSL_FILETYPE_PEM) != 1
                || SSL_CTX_use_PrivateKey_file(serverctx, privkeyfile,
                                               SSL_FILETYPE_PEM) != 1
                || SSL_CTX_check_private_key(serverctx) != 1)
            goto err;
    }

    if (sctx != NULL)
        *sctx = serverctx;
    if (cctx != NULL)
        *cctx = clientctx;
    return 1;

 err:
    if (sctx != NULL && *sctx == NULL)
        SSL_CTX_free(serverctx);
    if (cctx != NULL && *cctx == NULL)
        SSL_CTX_free(clientctx);
    return 0;
}

/*
 * NOTE: Transfers control of the BIOs - this function will free them on error.
 * There is no DTLS support at this stage.
 */
int perflib_create_ssl_objects(SSL_CTX *serverctx, SSL_CTX *clientctx,
                               SSL **sssl, SSL **cssl, BIO *s_to_c_fbio,
                               BIO *c_to_s_fbio)
{
    SSL *serverssl = NULL, *clientssl = NULL;
    BIO *s_to_c_bio = NULL, *c_to_s_bio = NULL;

    if (*sssl != NULL)
        serverssl = *sssl;
    else if ((serverssl = SSL_new(serverctx)) == NULL)
        goto error;
    if (*cssl != NULL)
        clientssl = *cssl;
    else if ((clientssl = SSL_new(clientctx)) == NULL)
        goto error;

    if ((s_to_c_bio = BIO_new(BIO_s_mem())) == NULL
            || (c_to_s_bio = BIO_new(BIO_s_mem())) == NULL)
        goto error;

    if (s_to_c_fbio != NULL
            && (s_to_c_bio = BIO_push(s_to_c_fbio, s_to_c_bio)) == NULL)
        goto error;
    if (c_to_s_fbio != NULL
            && (c_to_s_bio = BIO_push(c_to_s_fbio, c_to_s_bio)) == NULL)
        goto error;

    /* Set Non-blocking IO behaviour */
    BIO_set_mem_eof_return(s_to_c_bio, -1);
    BIO_set_mem_eof_return(c_to_s_bio, -1);

    /* Up ref these as we are passing them to two SSL objects */
    SSL_set_bio(serverssl, c_to_s_bio, s_to_c_bio);
    BIO_up_ref(s_to_c_bio);
    BIO_up_ref(c_to_s_bio);
    SSL_set_bio(clientssl, s_to_c_bio, c_to_s_bio);
    *sssl = serverssl;
    *cssl = clientssl;
    return 1;

 error:
    SSL_free(serverssl);
    SSL_free(clientssl);
    BIO_free(s_to_c_bio);
    BIO_free(c_to_s_bio);
    BIO_free(s_to_c_fbio);
    BIO_free(c_to_s_fbio);

    return 0;
}

#define MAXLOOPS    1000000

/*
 * Create an SSL connection, but does not read any post-handshake
 * NewSessionTicket messages.
 * We stop the connection attempt (and return a failure value) if either peer
 * has SSL_get_error() return the value in the |want| parameter. The connection
 * attempt could be restarted by a subsequent call to this function.
 */
int perflib_create_bare_ssl_connection(SSL *serverssl, SSL *clientssl, int want)
{
    int retc = -1, rets = -1, err, abortctr = 0, ret = 0;
    int clienterr = 0, servererr = 0;

    do {
        err = SSL_ERROR_WANT_WRITE;
        while (!clienterr && retc <= 0 && err == SSL_ERROR_WANT_WRITE) {
            retc = SSL_connect(clientssl);
            if (retc <= 0)
                err = SSL_get_error(clientssl, retc);
        }

        if (!clienterr && retc <= 0 && err != SSL_ERROR_WANT_READ) {
            printf("SSL_connect() failed %d, %d", retc, err);
            if (want != SSL_ERROR_SSL)
                ERR_print_errors_fp(stdout);
            clienterr = 1;
        }
        if (want != SSL_ERROR_NONE && err == want)
            goto err;

        err = SSL_ERROR_WANT_WRITE;
        while (!servererr && rets <= 0 && err == SSL_ERROR_WANT_WRITE) {
            rets = SSL_accept(serverssl);
            if (rets <= 0)
                err = SSL_get_error(serverssl, rets);
        }

        if (!servererr && rets <= 0
                && err != SSL_ERROR_WANT_READ
                && err != SSL_ERROR_WANT_X509_LOOKUP) {
            printf("SSL_accept() failed %d, %d", rets, err);
            if (want != SSL_ERROR_SSL)
                ERR_print_errors_fp(stdout);
            servererr = 1;
        }
        if (want != SSL_ERROR_NONE && err == want)
            goto err;
        if (clienterr && servererr)
            goto err;
        if (++abortctr == MAXLOOPS) {
            printf("No progress made");
            goto err;
        }
    } while (retc <=0 || rets <= 0);

    ret = 1;
 err:
    return ret;
}

/*
 * Create an SSL connection including any post handshake NewSessionTicket
 * messages.
 */
int perflib_create_ssl_connection(SSL *serverssl, SSL *clientssl, int want)
{
    int i;
    unsigned char buf;
    size_t readbytes;

    if (!perflib_create_bare_ssl_connection(serverssl, clientssl, want))
        return 0;

    /*
     * We attempt to read some data on the client side which we expect to fail.
     * This will ensure we have received the NewSessionTicket in TLSv1.3 where
     * appropriate. We do this twice because there are 2 NewSessionTickets.
     */
    for (i = 0; i < 2; i++) {
        if (SSL_read_ex(clientssl, &buf, sizeof(buf), &readbytes) > 0) {
            if (readbytes != 0) {
                printf("Unexpected data reading ticket\n");
                return 0;
            }
        } else if (SSL_get_error(clientssl, 0) != SSL_ERROR_WANT_READ) {
            printf("Unexpected error reading ticket\n");
            return 0;
        }
    }

    return 1;
}

void perflib_shutdown_ssl_connection(SSL *serverssl, SSL *clientssl)
{
    SSL_shutdown(clientssl);
    SSL_shutdown(serverssl);
    SSL_free(serverssl);
    SSL_free(clientssl);
}

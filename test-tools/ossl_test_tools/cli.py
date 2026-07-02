# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

"""CLI dispatcher.

Each subpackage that exposes user-facing functionality has a `register`
function which gets passed argparse's subparsers object.  To add a new
tool, write the subpackage, import it here, and call its register().
"""

import argparse

from . import crltest, ocsptest, pem, statem_clnt_construct_test


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="ossl-test-tools",
        description="Python helpers for OpenSSL test artifacts and tooling.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    crltest.register(sub)
    ocsptest.register(sub)
    pem.register(sub)
    statem_clnt_construct_test.register(sub)

    args = parser.parse_args(argv)
    return args.func(args) or 0

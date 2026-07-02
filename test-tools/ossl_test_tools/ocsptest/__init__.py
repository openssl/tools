# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

"""Generators for the artifacts in test/ocsptest.c.

Each subcommand writes its outputs back into the C source file, replacing
the existing kXxx[] declarations by variable name.
"""

from pathlib import Path

from . import pki


def _all_cmd(args):
    pki.build(args.source)
    print(f"regenerated all OCSP artifacts in {args.source}")


def register(subparsers):
    parent = subparsers.add_parser(
        "ocsptest",
        help="Regenerate artifacts in test/ocsptest.c.",
    )
    sub = parent.add_subparsers(dest="ocsptest_cmd", required=True)

    pki.register(sub)

    p = sub.add_parser("all", help="Run all OCSP artifact generators.")
    p.add_argument("--source", type=Path, required=True, help="Path to ocsptest.c")
    p.set_defaults(func=_all_cmd)

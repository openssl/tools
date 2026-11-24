# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

"""Generators for the indirect-CRL portions of test/crltest.c.

Each subcommand reads the inputs it needs from the C source file by
variable name (e.g. kRoot, kRootPrivateKey) and writes its outputs back
into the same file, replacing the existing kXxx[] declarations.
"""

from pathlib import Path

from . import alt_ta, delta, indirect, no_chain, two_dp


def _all_cmd(args):
    indirect.build(args.source)
    alt_ta.build(args.source)
    no_chain.build(args.source)
    delta.build(args.source)
    two_dp.build(args.source)
    print(f"regenerated all crltest artifacts in {args.source}")


def register(subparsers):
    parent = subparsers.add_parser(
        "crltest",
        help="Regenerate artifacts in test/crltest.c.",
    )
    sub = parent.add_subparsers(dest="crltest_cmd", required=True)

    indirect.register(sub)
    alt_ta.register(sub)
    no_chain.register(sub)
    delta.register(sub)
    two_dp.register(sub)

    p = sub.add_parser("all", help="Run indirect, alt-ta, no-chain, delta, and two-dp in order.")
    p.add_argument("--source", type=Path, required=True, help="Path to crltest.c")
    p.set_defaults(func=_all_cmd)

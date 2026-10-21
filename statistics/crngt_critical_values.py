#!/usr/bin/env python3

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# Run this using:
#   crngt_critical_values.py
#
# Then copy the arrays into:
#   providers/implementations/rands/fips_crng_test.c
#
# There is a dependency of scipi, include the package python3-scipy to resolve
# this.

from math import log2, ceil
from scipy.stats import binom

log_alpha = 40
alpha = 2**-log_alpha
H = ( 0.5, *range(1, 9) )
W = 512
rct = []
apt = []

def print_prob(name, probs):
    print("    /* alpha = 2^-%d */" % log_alpha)
    print("    static const unsigned int %s[9] = {" % name)
    print("        %d, /* H = 0.5 */" % probs[0])
    print("        ", end="")
    print(*probs[1:], sep=", ", end="")
    print(" /* H = 1, ..., 8 */")
    print("    };\n")

for h in H:
    rct = rct + [1 + ceil(log_alpha / h)]
    apt = apt + [round((1 + binom.ppf(1 - alpha, W, 2**-h)).item())]

print_prob("rct_c", rct);
print_prob("apt_c", apt);


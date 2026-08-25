# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Expected, operator-facing failures."""
from __future__ import annotations


class ReviewError(Exception):
    """Something the caller can act on: a bad reviewer, a failed lookup."""


class QueryError(ReviewError):
    """api.openssl.org could not be reached, or answered with a server error."""

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Fixtures for the reviewtools tests.

The fake person database lives in helpers.py; see the note in the
stagerelease conftest.
"""

from __future__ import annotations

from tests.reviewtools.helpers import frozen_time, people  # noqa: F401

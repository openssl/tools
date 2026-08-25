# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""Shared Python for the OpenSSL maintainer tools.

Two subpackages, so they can import each other with ordinary relative
imports rather than reaching across directories at runtime:

    stagerelease   release staging, driven by release-tools/stage-release
    reviewtools    PR review helpers, driven by review-tools/addrev and
                   friends

The executables stay in release-tools/ and review-tools/ because external
workflows -- Jenkins jobs, the ansible role that symlinks them into
/usr/local/bin -- invoke them by absolute path.  Each one puts this
directory on sys.path and imports from here; there is no install step.

Standard library only.
"""
from __future__ import annotations

__version__ = "1.0.0"

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""OpenSSL release staging.

Replaces release-tools/stage-release.sh, its release-aux/*.sh helpers and the
release-aux/fixup-*.pl scripts.  Standard library only: this runs on release
build hosts where installing packages is not always possible.
"""

from __future__ import annotations

__version__ = "1.0.0"

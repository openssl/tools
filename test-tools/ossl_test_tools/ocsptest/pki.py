# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

"""PKI for test/ocsptest.c.

  kOcspTestRoot     self-signed root CA, trust anchor and OCSP responder
  kOcspTestRootKey  the root CA private key, used to sign OCSP responses
  kOcspTestLeaf     leaf issued by the root CA

The chain is flat (no intermediate) so the root is the leaf's issuer and
therefore its authorized OCSP responder. Validity windows are long because
the verification path checks OCSP response validity against the wall clock.
"""

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID

from .. import cert_util

UTC = datetime.timezone.utc
NOT_BEFORE = datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
NOT_AFTER = datetime.datetime(2126, 1, 1, 0, 0, 0, tzinfo=UTC)

ROOT_DN = cert_util.name(
    "US", "California", "San Francisco",
    "Example Corp", "Certificate Authority",
    "Example Corp OCSP Test Root CA",
)
LEAF_DN = cert_util.name(
    "US", "California", "San Francisco",
    "Example Corp", "Web Services",
    "ocsp-leaf.example.com",
)


def _ca_key_usage():
    return x509.KeyUsage(
        digital_signature=True, content_commitment=False,
        key_encipherment=False, data_encipherment=False, key_agreement=False,
        key_cert_sign=True, crl_sign=True,
        encipher_only=False, decipher_only=False)


def _leaf_key_usage():
    return x509.KeyUsage(
        digital_signature=True, content_commitment=False,
        key_encipherment=True, data_encipherment=False, key_agreement=False,
        key_cert_sign=False, crl_sign=False,
        encipher_only=False, decipher_only=False)


def build(source_path):
    root_key = cert_util.new_rsa_key()
    root = (
        x509.CertificateBuilder()
        .subject_name(ROOT_DN)
        .issuer_name(ROOT_DN)
        .public_key(root_key.public_key())
        .serial_number(0x1)
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(NOT_AFTER)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(_ca_key_usage(), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),
            critical=False)
        .sign(private_key=root_key, algorithm=hashes.SHA256())
    )

    leaf_key = cert_util.new_rsa_key()
    leaf = (
        x509.CertificateBuilder()
        .subject_name(LEAF_DN)
        .issuer_name(ROOT_DN)
        .public_key(leaf_key.public_key())
        .serial_number(0x1000)
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(NOT_AFTER)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_leaf_key_usage(), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
            critical=False)
        .add_extension(cert_util.akid_from_cert(root), critical=False)
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("ocsp-leaf.example.com")]),
            critical=False)
        .sign(private_key=root_key, algorithm=hashes.SHA256())
    )

    cert_util.update_cert_in_c(source_path, "kOcspTestRoot", root)
    cert_util.update_key_in_c(source_path, "kOcspTestRootKey", root_key)
    cert_util.update_cert_in_c(source_path, "kOcspTestLeaf", leaf)


def _cmd(args):
    build(args.source)
    print(f"updated kOcspTestRoot kOcspTestRootKey kOcspTestLeaf in {args.source}")


def register(sub):
    p = sub.add_parser(
        "pki",
        help="Regenerate the root CA, root key, and leaf.",
    )
    p.add_argument("--source", type=Path, required=True, help="Path to ocsptest.c")
    p.set_defaults(func=_cmd)

# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

"""Artifacts for a certificate whose CRL distribution points split the
revocation reasons between them.

  kLeafTwoDP   leaf signed by kRoot with two CRL distribution points:
                 http://crl.example.com/a.crl  REASONS_A
                 http://crl.example.com/b.crl  REASONS_B
               which together cover all eight reasons
  kCrlTwoDPA   empty CRL signed by kRoot, IDP scoped to a.crl / REASONS_A
  kCrlTwoDPB   empty CRL signed by kRoot, IDP scoped to b.crl / REASONS_B

Neither CRL covers all reasons on its own, so verification with
X509_V_FLAG_EXTENDED_CRL_SUPPORT only succeeds once both have been used.
This exercises the accumulation of reasons across the iterations of
check_cert_crl(), including for CRLs returned by a get_crl callback.

kRoot, kRootPrivateKey and kLeafPrivateKey are read out of the source
file by name; the leaf reuses kLeafPrivateKey rather than a fresh key.
"""

from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import ReasonFlags
from cryptography.x509.oid import NameOID

from .. import cert_util
from ._shared import CERT_NOT_BEFORE, CRL_LAST_UPDATE, CRL_NEXT_UPDATE, LEAF_NOT_AFTER

LEAF_DN = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME,      "US"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example Corp"),
    x509.NameAttribute(NameOID.COMMON_NAME,       "twodp.example.com"),
])

URI_A = "http://crl.example.com/a.crl"
URI_B = "http://crl.example.com/b.crl"

# Must match TWO_DP_REASONS_A (0x0078) and TWO_DP_REASONS_B (0x8007) in
# crltest.c, which use the representation of X509_STORE_CTX_set_current_reasons().
REASONS_A = frozenset({
    ReasonFlags.key_compromise,
    ReasonFlags.ca_compromise,
    ReasonFlags.affiliation_changed,
    ReasonFlags.superseded,
})
REASONS_B = frozenset({
    ReasonFlags.cessation_of_operation,
    ReasonFlags.certificate_hold,
    ReasonFlags.privilege_withdrawn,
    ReasonFlags.aa_compromise,
})


def _dp(uri, reasons):
    return x509.DistributionPoint(
        full_name=[x509.UniformResourceIdentifier(uri)],
        relative_name=None,
        reasons=reasons,
        crl_issuer=None,
    )


def _scoped_crl(root_cert, root_key, akid, uri, reasons, number):
    return (
        x509.CertificateRevocationListBuilder()
        .issuer_name(root_cert.subject)
        .last_update(CRL_LAST_UPDATE)
        .next_update(CRL_NEXT_UPDATE)
        .add_extension(akid, critical=False)
        .add_extension(
            x509.IssuingDistributionPoint(
                full_name=[x509.UniformResourceIdentifier(uri)],
                relative_name=None,
                only_contains_user_certs=False, only_contains_ca_certs=False,
                only_some_reasons=reasons, indirect_crl=False,
                only_contains_attribute_certs=False),
            critical=True)
        .add_extension(x509.CRLNumber(number), critical=False)
        .sign(private_key=root_key, algorithm=hashes.SHA256())
    )


def build(source_path):
    root_cert = cert_util.cert_from_c(source_path, "kRoot")
    root_key = cert_util.key_from_c(source_path, "kRootPrivateKey")
    leaf_key = cert_util.key_from_c(source_path, "kLeafPrivateKey")
    akid = cert_util.akid_from_cert(root_cert)

    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(LEAF_DN)
        .issuer_name(root_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(0x1001)
        .not_valid_before(CERT_NOT_BEFORE)
        .not_valid_after(LEAF_NOT_AFTER)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=True, data_encipherment=False, key_agreement=False,
                key_cert_sign=False, crl_sign=False,
                encipher_only=False, decipher_only=False),
            critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
            critical=False)
        .add_extension(akid, critical=False)
        .add_extension(
            x509.CRLDistributionPoints([
                _dp(URI_A, REASONS_A),
                _dp(URI_B, REASONS_B),
            ]),
            critical=False)
        .sign(private_key=root_key, algorithm=hashes.SHA256())
    )

    crl_a = _scoped_crl(root_cert, root_key, akid, URI_A, REASONS_A, 1)
    crl_b = _scoped_crl(root_cert, root_key, akid, URI_B, REASONS_B, 2)

    cert_util.update_cert_in_c(source_path, "kLeafTwoDP", leaf_cert)
    cert_util.update_crl_in_c(source_path, "kCrlTwoDPA", crl_a)
    cert_util.update_crl_in_c(source_path, "kCrlTwoDPB", crl_b)


def _cmd(args):
    build(args.source)
    print(f"updated kLeafTwoDP kCrlTwoDPA kCrlTwoDPB in {args.source}")


def register(sub):
    p = sub.add_parser(
        "two-dp",
        help="Regenerate the leaf with two reason-split CRL distribution "
             "points and a scoped CRL for each.",
    )
    p.add_argument("--source", type=Path, required=True, help="Path to crltest.c")
    p.set_defaults(func=_cmd)

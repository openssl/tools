# Revocation Recipient Certificates

This directory contains the public OpenPGP certificates used by the OpenSSL
OpenPGP certificate initialization pipeline to encrypt the primary-key
revocation certificate artifact.

`recipients.txt` is the authoritative recipient manifest.  Each non-comment
line contains:

```text
<40-hex-character fingerprint> <email>
```

For each manifest entry, this directory must contain a public certificate named:

```text
<fingerprint>.pgp
```

The pipeline validates that each certificate contains the expected fingerprint
and User ID email, and that `sq encrypt --for-file` can encrypt to the
certificate under the current `sq` policy.

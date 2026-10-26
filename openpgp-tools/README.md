# OpenPGP key-lifecycle tools

This directory contains the tools that manage the lifecycle of the OpenPGP key
used to sign OpenSSL release artifacts.  The key material lives in an Entrust
nShield HSM (Security World); these scripts never touch private key bytes, they
only drive the nShield tooling and [`sq-pkcs11`](https://github.com/openssl/sq-pkcs11)
to produce OpenPGP certificates and revocation certificates.

## Contents

- `openssl-pgp` — the main driver.  Implements the
  [artifact signing policy](https://openssl-library.org/policies/general/artifact-signing-policy/)
  on top of `sq-pkcs11` (which speaks PKCS#11 to the HSM) and the nShield
  utilities (`generatekey`, `cklist`, `nfkminfo`, `preload`).  Commands:

  | Command | Purpose |
  | --- | --- |
  | `primary-generate` | generate the OCS-protected RSA-4096 primary key |
  | `subkey-generate` | generate a module-protected RSA-4096 signing subkey |
  | `cert-init` | issue the published certificate plus an offline primary revocation certificate |
  | `subkey-rotate` | bind a new signing subkey into the published certificate |
  | `cert-revoke` | issue a primary-key revocation certificate |
  | `subkey-revoke` | revoke a subkey by fingerprint, using only the primary key |

  Configuration comes from environment variables (`OPENSSL_PGP_*`), optionally
  sourced from a config file — `$OPENSSL_PGP_CONFIG`, or `openssl-pgp.conf`
  next to the script.  Run `openssl-pgp --help` for the full list.

  Policy enforced by the script: RSA-4096 keys, `logkeyusage=yes` for Security
  World audit logging, primary protected by the configured K/N OCS with 5y
  validity, signing subkeys module-protected with 1y validity, and certificate
  timestamps derived from the nShield `gentime` rather than the wall clock.
  Labels and cardsets are validated against the Security World before any
  destructive HSM action runs.

- `openssl-pgp-ceremony-run` — runs an attended OCS ceremony from an automation
  server without ever routing card passphrases through it.  It starts the
  requested `openssl-pgp` command in a detached `tmux` session on the HSM
  client and waits for its exit status; custodians SSH to that host, attach to
  the session, present their cards and type OCS passphrases directly into the
  shared terminal. The automation server stays an orchestrator and audit
  collector only.

- `openssl-pgp-revocation-recipients` — validates the revocation-certificate
  recipients and produces an encryption bundle: it checks each recipient
  certificate's fingerprint, User ID email, and usability under the current `sq`
  policy, then emits a concatenated certificate bundle, a recipient manifest,
  and the bundle's SHA-256 checksum.

- `revocation-recipients/` — the recipient set consumed by the above:
  `recipients.txt` (the authoritative `<fingerprint> <email>` manifest) and one
  `<fingerprint>.pgp` public certificate per entry.  See the README in that
  directory.

## Requirements

- [`sq-pkcs11`](https://github.com/openssl/sq-pkcs11) on `PATH` (or
  `OPENSSL_PGP_SQ_PKCS11` pointing at it), plus `sq` for the recipient tooling.
- nShield client tooling under `/opt/nfast` and access to the Security World.
- `tmux` on the HSM client, for `openssl-pgp-ceremony-run`.

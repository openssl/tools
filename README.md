# OpenSSL tools

A collection of tools and instructions useful in OpenSSL development.

Most sets of tools are in their own subdirectory with their own README:

| Directory | What it holds |
| --- | --- |
| [`release-tools/`](release-tools/README.md) | staging an OpenSSL release |
| [`review-tools/`](review-tools/README.md) | reviewing and merging pull requests |
| [`openpgp-tools/`](openpgp-tools/README.md) | the release signing key's lifecycle |
| [`OpenSSL-Query/`](OpenSSL-Query/README.md) | Perl client for the committer and CLA database; no longer used by anything here |
| `nist-conversion/` | converting NIST DRBG test vectors for `evp_test` |
| `statistics/` | generating test data for the OpenSSL source tree |

`lib/` is the exception: it is not a set of tools but the shared Python that
`release-tools` and `review-tools` are both built from, with one test suite
covering both.  The executables stay in their own directories because
external workflows invoke them by absolute path.

Instructions that span more than one set of tools are in this top directory:

- [HOWTO-release.md](HOWTO-release.md) — the whole release process
- [HOWTO-handle-security-issue.md](HOWTO-handle-security-issue.md) — handling
  an embargoed security issue, up to and including its release

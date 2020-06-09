This directory contains tools that are used to convert between NIST supplied
test data sets and internal formats.

The `convert_nist_drbg_test_data.lua` script converts the
[NIST DRBG test data]: https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/drbg/drbgtestvectors.zip
to a format suitable for use in evp_test.

The `drbgtestvectors.zip` file contains the DRGB test vectors that the
`convert_nist_drbg_test_data.lua` script converted for the current OpenSSL
source repository.

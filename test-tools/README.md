# ossl-test-tools

Python tools for OpenSSL's C tests. They generate test artifacts (certs,
CRLs, keys) and edit them into the `.c` source files in place, replacing
the existing `static const ... kName[]` declarations by variable name.

## Setup

    cd test-tools
    uv sync

## Use

The first argument names the test to update. It matches the `.c` file it
generates artifacts for, e.g. `crltest` for `test/crltest.c` and
`ocsptest` for `test/ocsptest.c`. After that comes the generator
subcommand. Run `--help` at any level to see what is available and the
parameters each subcommand takes:

    uv run ossl-test-tools --help
    uv run ossl-test-tools crltest --help
    uv run ossl-test-tools ocsptest --help

The generator subcommands take a `--source` pointing at the `.c` file to
rewrite, and `all` regenerates every artifact for that test:

    uv run ossl-test-tools crltest all       --source path/to/crltest.c
    uv run ossl-test-tools crltest indirect  --source path/to/crltest.c
    uv run ossl-test-tools ocsptest all      --source path/to/ocsptest.c

`pem-to-c` formats a PEM file as a C declaration and prints it to stdout,
for one-off pasting:

    uv run ossl-test-tools pem-to-c some.pem --name kSomething

## Adding a new variable

Add an empty placeholder to the `.c` file:

    static const char *kSomething[] = {};

Then run the relevant subcommand. The placeholder gets populated.

## Adding a new generator

A subpackage of `ossl_test_tools` exposing `register(subparsers)`. Import
and register it from `cli.py`.

Two helpers worth knowing:

* `csource` locates, reads, and rewrites `static const ... kName[]`
  arrays. PEM string arrays and hex byte arrays are both supported for
  reading; only PEM is written.
* `cert_util` provides cert/CRL/key builders plus `cert_from_c` /
  `update_cert_in_c` bridges.

Per-tool constants (DNs, validity windows, serials) stay in the tool's
own module.

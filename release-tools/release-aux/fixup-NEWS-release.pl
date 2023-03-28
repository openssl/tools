#! /usr/bin/env perl -p

BEGIN {
    our $count = 1;              # Only the first one
    our $RELEASE_TEXT = $ENV{RELEASE_TEXT};
    our $RELEASE_DATE = $ENV{RELEASE_DATE};
}

if (/^  Major changes between OpenSSL (\S+) and OpenSSL (\S+) \[under development\]/
    && $count-- > 0) {
    $_ = "  Major changes between OpenSSL $1 and OpenSSL $RELEASE_TEXT [$RELEASE_DATE]$'";
}

#! /usr/bin/env perl -p

BEGIN {
    our $count = 1;              # Only the first one
    our $RELEASE = $ENV{RELEASE};
}

if (/^ OpenSSL.*$/ && $count-- > 0) {
    $_ = " OpenSSL $RELEASE$'";
}

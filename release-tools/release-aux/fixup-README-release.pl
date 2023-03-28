#! /usr/bin/env perl -p

BEGIN {
    our $count = 1;              # Only the first one
    our $RELEASE = $ENV{RELEASE};
    our $RELEASE_TEXT = $ENV{RELEASE_TEXT};
    our $RELEASE_DATE = $ENV{RELEASE_DATE};
}

if (/^ OpenSSL.*$/ && $count-- > 0) {
    $_ = " OpenSSL $RELEASE $RELEASE_DATE$'";
}

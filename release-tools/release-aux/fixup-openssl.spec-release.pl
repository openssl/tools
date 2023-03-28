#! /usr/bin/env perl -p

BEGIN {
    our $count = 1;              # Only the first one
    our $RELEASE = $ENV{RELEASE};
    our $ispre = $RELEASE =~ /-pre/;

    $RELEASE =~ s/-dev$//;
}

if (!$ispre && /^Version:\s+(\S+)$/ && $count-- > 0) {
    $_ = "Version: $RELEASE$'";
}

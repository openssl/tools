#!perl -T
use 5.006;
use strict;
use warnings;
use Test::More;

plan tests => 1;

BEGIN {
    use_ok( 'OpenSSL::Query::REST' ) || print "Bail out!\n";
}

#note( "Testing OpenSSL::Query $OpenSSL::Query::VERSION, Perl $], $^X" );

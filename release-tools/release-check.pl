#! /usr/bin/env perl
# Copyright 2010-2018 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;

sub check_str {
    my ( $message, $expected, $value, $pok ) = @_;
    die "Bad checkstr values for $message"
      if !defined $value || !defined $expected;
    if ( $value ne $expected ) {
        print
          "$message: check failed, expecting \"$expected\", got \"$value\"!!\n";
        $$pok = 0;
    } elsif ($main::debug) {
        print "$message: checking \"$value\" against \"$expected\"\n";
    }
}

# Check syntax of README file.

sub openssl_check_README {
    my ( $version, $indate ) = @_;
    my $ok   = 1;
    my $date = openssl_date($indate);
    open( IN, "README" ) || die "Can't open README";
    while (<IN>) {
        if (/^.*OpenSSL\s+(\S+)\s+(\([[:alpha:]]+\)\s+)?(.*)$/) {
            check_str( "README version", $version, $1, \$ok );
            if ( defined $indate ) {
                check_str( "README date", $date, $3, \$ok );
            }
            close IN;
            return $ok;
        }
    }
    close IN;
    print STDERR "Invalid syntax in README\n";
    return 0;
}

sub openssl_check_NEWS {
    my ( $version, $prev, $indate ) = @_;
    my $date = openssl_date( $version =~ /-pre/ ? undef : $indate );
    my $ok = 1;
    if ( $date =~ /XXX/ ) {
        if ( $version =~ /-pre/ ) {
            $date = "in pre-release";
        } else {
            $date = "under development";
        }
    }
    $version =~ s/-dev$//;
    $version =~ s/-pre.*$//;
    open( IN, "NEWS" ) || die "Can't open NEWS";

    while (<IN>) {
        if (
/^  Major changes between OpenSSL (\S+) and OpenSSL (\S+)\s+\[0?(.*)\]/
          )
        {
            check_str( "NEWS previous version", $prev,    $1, \$ok );
            check_str( "NEWS version",          $version, $2, \$ok );
            check_str( "NEWS date",             $date,    $3, \$ok );
            close IN;
            return $ok;
        }
    }
    close IN;
    print STDERR "Invalid syntax in NEWS\n";
    return 0;
}

sub openssl_check_CHANGES {
    my ( $version, $prev, $indate ) = @_;
    my $date = openssl_date( $version =~ /-pre/ ? undef : $indate );
    my $ok = 1;
    $version =~ s/-dev$//;
    $version =~ s/-pre.*$//;
    open( IN, "CHANGES" ) || die "Can't open CHANGES";

    while (<IN>) {
        if (/^ Changes between (\S+) and (\S+)\s+\[0?(.*)\]/) {
            check_str( "CHANGES previous version", $prev,    $1, \$ok );
            check_str( "CHANGES version",          $version, $2, \$ok );
            check_str( "CHANGES date",             $date,    $3, \$ok );
            close IN;
            return $ok;
        }
    }
    close IN;
    print STDERR "Invalid syntax in CHANGES\n";
    return 0;
}

sub openssl_check_version_h {
    my ( $version, $indate ) = @_;
    my ( $hex_done, $fips_done, $version_done );
    my $hexversion   = openssl_version_hex($version);
    my $ok           = 1;
    my $version_fips = $version . "-fips";
    $version_fips =~ s/-dev-fips/-fips-dev/;
    my $date = openssl_date($indate);
    open( IN, "$main::includepath/opensslv.h" ) || die "Can't open opensslv.h";

    while (<IN>) {
        if (/OPENSSL_VERSION_NUMBER\s+(0x[0-9a-f]+)L/) {
            check_str( "opensslv.h: HEX version", $hexversion, $1, \$ok );
            $hex_done = 1;
        } elsif (
/OPENSSL_VERSION_TEXT\s+\"OpenSSL (\S*)\s+(\([[:alpha:]]+\)\s+)?(.*)\"/
          )
        {
            check_str( "opensslv.h: version", $version, $1, \$ok );
            check_str( "opensslv.h: date",    $date,    $3, \$ok );
            $version_done = 1;
        }
        if ( $hex_done && $version_done ) {
            close IN;
            return $ok;
        }
    }
    print STDERR "Invalid syntax in opensslv.h\n";
    close IN;
    return 0;
}

sub openssl_check_spec {
    my ($version) = @_;
    my $ok = 1;
    $version =~ s/-dev$//;
    $version =~ s/-pre.*$//;
    open( IN, "openssl.spec" ) || die "Can't open openssl.spec";
    while (<IN>) {
        if (/^Version:\s+(\S+)$/) {
            check_str( "openssl.spec version", $version, $1, \$ok );
            close IN;
            return $ok;
        }
    }
    close IN;
    print STDERR "Invalid syntax in README\n";
    return 0;
}

sub print_ok {
    my ( $file, $ok ) = @_;
    print "File: $file " . ( $ok ? "OK" : "NOT OK!!" ) . "\n"
      if ($main::verbose);
}

sub openssl_check_all {
    my ( $version, $last_version, $date ) = @_;

    my $readme_ok = openssl_check_README( $version, $date );

    print_ok( "README", $readme_ok );

    my $changes_ok = openssl_check_CHANGES( $version, $last_version, $date );

    print_ok( "CHANGES", $changes_ok );

    my $news_ok = openssl_check_NEWS( $version, $last_version, $date );

    print_ok( "NEWS", $news_ok );

    my $v_h_ok = openssl_check_version_h( $version, $date );

    print_ok( "opensslv.h", $v_h_ok );

    # Newer versions don't have openssl.spec
    my $spec_ok = 1;
    if ( -f "openssl.spec" ) {
        $spec_ok = openssl_check_spec($version);

        print_ok( "openssl.spec", $spec_ok );
    }

    return $readme_ok && $changes_ok && $news_ok && $v_h_ok && $spec_ok;
}

# If there are no tagged releases for the current version
# and we are in pre release mode then either we are just entering
# pre release and the next version will be pre1-dev or we are already
# at pre1-dev and we need to do a release of pre1.
# Check opensslv.h to determine which

sub openssl_check_first_pre {
    open( IN, "$main::includepath/opensslv.h" ) || die "Can't open opensslv.h";

    while (<IN>) {
        if (/OPENSSL_VERSION_TEXT\s+\"OpenSSL \S*\s+.*\"/) {
            close IN;

            # Ignore -fips in string
            s/-fips//;
            return /pre1-dev/;
        }
    }
    close IN;
    die "Invalid sysntax in opensslv.h";
}

return 1;

#! /usr/bin/env perl
# Copyright 2010-2018 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;
use warnings;

sub openssl_update_file {
    my $fref     = pop @_;
    my $file     = pop @_;
    my $file_new = $file . ".new";
    my $finished = 0;
    open( IN,  "$file" )      || die "Can't open $file";
    open( OUT, ">$file_new" ) || die "Can't open $file_new";
    while (<IN>) {
        $finished = &$fref(@_) unless $finished;
        print OUT;
    }
    close IN;
    close OUT;
    unlink $file;
    rename $file_new, $file;
    print "Updated $file\n" if $main::verbose;
}

sub openssl_update_README {
    my ( $version, $indate, $label ) = @_;
    my $date   = openssl_date($indate);
    my $update = sub {
        if (/^.*OpenSSL/) {
            $_ = " OpenSSL $version";
            $_ .= " $label" if ( defined $label );
            $_ .= " $date"  if ( defined $indate );
            $_ .= "\n";
            return 1;
        }
        return 0;
    };
    openssl_update_file( @_, "README", $update );
}

sub openssl_update_CHANGES {
    my ( $version, $indate ) = @_;
    my $date = openssl_date($indate);
    $version =~ s/-dev//;
    my $update = sub {
        if (/^ Changes between \S+ and (\S+)\s+\[0?(.*)\]/) {
            my $chversion = $1;
            my $chdate    = $2;
            if ( defined $indate ) {
                s/$chdate/$date/;
            } else {
                my $newchanges = <<END;
 Changes between $chversion and $version [xx XXX xxxx]

  *)

END
                $_ = $newchanges . $_;
            }
            return 1;
        }
        return 0;
    };
    openssl_update_file( @_, "CHANGES", $update );
}

sub openssl_update_NEWS {
    my ( $version, $indate ) = @_;
    my $date;
    if ( $version =~ /-pre1-dev/ ) {
        $date   = "in pre-release";
        $indate = "";
    } elsif ( $version =~ /-pre/ ) {
        return 1;
    } else {
        $date = openssl_date($indate);
    }
    $version =~ s/-dev//;
    my $update = sub {
        if (
/^  Major changes between OpenSSL \S+ and OpenSSL (\S+)\s+\[0?(.*)\]/
          )
        {
            my $chversion = $1;
            my $chdate    = $2;
            if ( defined $indate ) {
                s/$chdate/$date/;
            } else {
                my $newchanges = <<END;
  Major changes between OpenSSL $chversion and OpenSSL $version [under development]

      o

END
                $_ = $newchanges . $_;
            }
            return 1;
        }
        return 0;
    };
    openssl_update_file( @_, "NEWS", $update );
}

sub openssl_update_version_h {
    my ( $version, $indate, $label ) = @_;
    my $hexversion   = openssl_version_hex($version);
    my $date         = openssl_date($indate);
    my $version_fips = $version . "-fips";
    $version_fips =~ s/-dev-fips/-fips-dev/;
    if ( !defined $label ) {
        $label = "";
    }
    my $update = sub {
        if (/(#\s*define\s+OPENSSL_VERSION_NUMBER\s+)/) {
            $_ = "${1}${hexversion}L\n";
        } elsif (/(#\s*define\s+OPENSSL_VERSION_TEXT\s+).*fips/) {
            $_ = "${1}\"OpenSSL $version_fips $label $date\"\n";
        } elsif (/(#\s*define\s+OPENSSL_VERSION_TEXT\s+)/) {
            $_ = "${1}\"OpenSSL $version $label $date\"\n";
        }
        return 0;
    };
    openssl_update_file( @_, "$main::includepath/opensslv.h", $update );
}

sub openssl_update_spec {
    my ($version) = @_;
    $version =~ s/-dev$//;
    my $update = sub {
        s/^Version:\s+(\S+)$/Version: $version/;
    };
    openssl_update_file( @_, "openssl.spec", $update );
}

sub openssl_update_all {
    my ( $version, $date, $label ) = @_;
    my $ispre = $version =~ /-pre/;
    if ( defined $label ) {
        $label = "($label)";
    }
    openssl_update_version_h( $version, $date, $label );
    openssl_update_spec($version) if ( !$ispre && -f "openssl.spec" );
    openssl_update_README( $version, $date, $label );
    openssl_update_CHANGES( $version, $date ) unless $ispre;
    openssl_update_NEWS( $version, $date );
}

return 1;

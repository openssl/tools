#! /usr/bin/env perl
# Copyright 2010-2018 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# Return date into a form suitable for the FAQ, version file and
# CHANGES file entries. Optionally can be passed date in the form
# mm/dd/yyyy

sub openssl_date {
    my ($datestr) = @_;
    my ( $mday, $mon, $year );

    if ( defined $datestr ) {
        if ( $datestr =~ /(\d+)\/(\d+)\/(\d+)/ ) {
            $mday = $1;
            $mon  = $2;
            $year = $3;
            $mon--;
        } else {
            die "Invalid date syntax $datestr, expecting mm/dd/yyyy";
        }
    } else {
        return ( "xx XXX xxxx", undef, undef ) if wantarray;
        return "xx XXX xxxx";
    }

    my $mdsuff;
    if ( $mday % 10 > 0 && $mday % 10 <= 3 && ( $mday < 10 || $mday > 20 ) ) {
        my @mday_ord = qw(st nd rd);
        $mdsuff = $mday_ord[ $mday % 10 - 1 ];
    } else {
        $mdsuff = "th";
    }

    my @mnames =
      qw(January February March April May June July August September October November December);

    my $mname = $mnames[$mon];
    my $mname_short = substr $mname, 0, 3;

    my $date_ch = sprintf "%d %s %d", $mday, $mname_short, $year;
    return $date_ch unless wantarray;
    my $date_ab = sprintf "%s %d%s, %d", $mname_short, $mday, $mdsuff, $year;
    my $date_full = sprintf "%-9s %2d%s, %d", $mname, $mday, $mdsuff, $year;

    return ( $date_ch, $date_ab, $date_full );

}

# Return current date in dd/mm/yyyy format suitable to passing into
# openssl_date().

sub openssl_current_date {
    my ( $mday, $mon, $year ) = (localtime)[ 3 .. 5 ];
    $year += 1900;
    $mon++;
    return "$mday/$mon/$year";
}

return 1;
